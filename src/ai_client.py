"""Unified AI provider client for text generation."""

import http
import logging

import httpx

from src import const
from src.config import settings

logger = logging.getLogger(__name__)


def _strip_backticks(text: str) -> str:
    """Strip markdown code block wrappers from AI response."""
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text


async def _gemini_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call Google Gemini API."""
    if not settings.gemini_api_key:
        logger.warning("Gemini API key not configured")
        return None

    headers = {
        "x-goog-api-key": settings.gemini_api_key,
        "content-type": "application/json",
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    url = f"{const.GEMINI_API_BASE}/v1beta/models/{settings.gemini_model}:generateContent"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=30.0)
            if response.status_code == http.HTTPStatus.OK:
                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    logger.error("Gemini returned empty candidates")
                    return None
                return candidates[0]["content"]["parts"][0]["text"]
            logger.error("Gemini API error, status: %s", response.status_code)
            return None
    except httpx.HTTPError as exc:
        logger.error("Gemini API request failed: %s", exc)
        return None


async def _anthropic_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call Anthropic Messages API."""
    if not settings.anthropic_api_key:
        logger.warning("Anthropic API key not configured")
        return None

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{const.ANTHROPIC_API_BASE}/v1/messages",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            if response.status_code == http.HTTPStatus.OK:
                data = response.json()
                return data["content"][0]["text"]
            logger.error("Anthropic API error, status: %s", response.status_code)
            return None
    except httpx.HTTPError as exc:
        logger.error("Anthropic API request failed: %s", exc)
        return None


async def _openai_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call OpenAI Chat Completions API."""
    if not settings.gpt_token:
        logger.warning("OpenAI API key not configured")
        return None

    headers = {
        "authorization": f"Bearer {settings.gpt_token}",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.gpt_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{const.OPENAI_API_BASE}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            if response.status_code == http.HTTPStatus.OK:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            logger.error("OpenAI API error, status: %s", response.status_code)
            return None
    except httpx.HTTPError as exc:
        logger.error("OpenAI API request failed: %s", exc)
        return None


_PROVIDERS = {
    const.PROVIDER_GEMINI: _gemini_complete,
    const.PROVIDER_ANTHROPIC: _anthropic_complete,
    const.PROVIDER_OPENAI: _openai_complete,
}


async def _ai_complete(
    provider: str, prompt: str, max_tokens: int, temperature: float
) -> str | None:
    """Dispatch AI call to the configured provider."""
    handler = _PROVIDERS.get(provider)
    if not handler:
        logger.error("Unknown AI provider: %s", provider)
        return None
    raw = await handler(prompt, max_tokens, temperature)
    if raw is None:
        return None
    return _strip_backticks(raw)


async def classify_text(prompt: str) -> str | None:
    """Classify text using the configured categorization provider."""
    return await _ai_complete(
        settings.categorization_provider, prompt, max_tokens=50, temperature=0.0
    )


async def cleanup_text(prompt: str, max_tokens: int) -> str | None:
    """Clean up text using the configured GPT provider."""
    return await _ai_complete(settings.gpt_provider, prompt, max_tokens=max_tokens, temperature=0.0)


async def gpt_chat(prompt: str) -> str | None:
    """Generate a chat response using the configured GPT provider."""
    return await _ai_complete(settings.gpt_provider, prompt, max_tokens=2048, temperature=0.7)
