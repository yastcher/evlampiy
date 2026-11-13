"""Messages-based AI chat completion with tool calling support.

Unlike ai_client.py (prompt-based, returns plain str), this module works with
message lists and structured responses including tool calls. Supports all
provider formats: OpenAI-compatible, Gemini, Anthropic.
"""

import asyncio
import dataclasses
import http
import logging
import typing

import httpx

from evlampiy import ai_client, const, llm_proxy
from evlampiy.ai import _mask
from evlampiy.ai.chat_formats import (
    ChatResponse,
    messages_to_anthropic,
    messages_to_gemini,
    parse_anthropic_response,
    parse_gemini_response,
    parse_openai_response,
    tools_to_anthropic,
    tools_to_gemini,
    tools_to_openai,
)
from evlampiy.ai_client import OpenAIEndpoint, RateLimitError
from evlampiy.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAYS = (2.0, 4.0, 8.0)
_HTTP_5XX_MIN = http.HTTPStatus.INTERNAL_SERVER_ERROR


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


async def _openai_chat_complete(
    endpoint: OpenAIEndpoint,
    messages: list[dict[str, typing.Any]],
    tools: list[dict[str, typing.Any]] | None,
    max_tokens: int,
    temperature: float,
) -> ChatResponse | None:
    """Call an OpenAI-compatible Chat Completions API with tool support."""
    headers = {
        "authorization": f"Bearer {endpoint.api_key}",
        "content-type": "application/json",
    }
    payload: dict[str, typing.Any] = {
        "model": endpoint.model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools_to_openai(tools)

    client = await ai_client.get_http_client()
    response = await client.post(endpoint.url, headers=headers, json=payload)

    if response.status_code == http.HTTPStatus.OK:
        return parse_openai_response(response.json())

    if response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
        raise RateLimitError(endpoint.provider)

    if response.status_code >= _HTTP_5XX_MIN:
        raise _ServerError(f"{endpoint.provider} server error: {response.status_code}")

    logger.error(
        "%s chat API error, status: %s, body: %.300s",
        endpoint.provider,
        response.status_code,
        response.text,
    )
    return None


async def _gemini_chat_complete(
    messages: list[dict[str, typing.Any]],
    tools: list[dict[str, typing.Any]] | None,
    max_tokens: int,
    temperature: float,
) -> ChatResponse | None:
    """Call Google Gemini API with tool support."""
    if not settings.gemini_api_key:
        logger.warning("Gemini API key not configured")
        return None

    system_text, contents = messages_to_gemini(messages)

    headers = {
        "x-goog-api-key": settings.gemini_api_key,
        "content-type": "application/json",
    }
    payload: dict[str, typing.Any] = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}
    if tools:
        payload["tools"] = tools_to_gemini(tools)

    base = llm_proxy.api_base(const.PROVIDER_GEMINI, const.GEMINI_API_BASE)
    url = f"{base}/v1beta/models/{settings.gemini_model}:generateContent"

    client = await ai_client.get_http_client()
    response = await client.post(url, headers=headers, json=payload)

    if response.status_code == http.HTTPStatus.OK:
        return parse_gemini_response(response.json())

    if response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
        raise RateLimitError(const.PROVIDER_GEMINI)

    if response.status_code >= _HTTP_5XX_MIN:
        raise _ServerError(f"Gemini server error: {response.status_code}")

    logger.error("Gemini chat API error, status: %s, body: %.300s", response.status_code, response.text)
    return None


async def _anthropic_chat_complete(
    messages: list[dict[str, typing.Any]],
    tools: list[dict[str, typing.Any]] | None,
    max_tokens: int,
    temperature: float,
) -> ChatResponse | None:
    """Call Anthropic Messages API with tool support."""
    if not settings.anthropic_bot_api_key:
        logger.warning("Anthropic API key not configured")
        return None

    system_text, anthropic_messages = messages_to_anthropic(messages)

    headers = {
        "x-api-key": settings.anthropic_bot_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: dict[str, typing.Any] = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "messages": anthropic_messages,
        "temperature": temperature,
    }
    if system_text:
        payload["system"] = system_text
    if tools:
        payload["tools"] = tools_to_anthropic(tools)

    client = await ai_client.get_http_client()
    response = await client.post(
        f"{llm_proxy.api_base(const.PROVIDER_ANTHROPIC, const.ANTHROPIC_API_BASE)}/v1/messages",
        headers=headers,
        json=payload,
    )

    if response.status_code == http.HTTPStatus.OK:
        return parse_anthropic_response(response.json())

    if response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
        raise RateLimitError(const.PROVIDER_ANTHROPIC)

    if response.status_code >= _HTTP_5XX_MIN:
        raise _ServerError(f"Anthropic server error: {response.status_code}")

    logger.error("Anthropic chat API error, status: %s", response.status_code)
    return None


class _ServerError(Exception):
    """Internal: server-side error (5xx), eligible for retry."""


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------

_OPENAI_COMPATIBLE = frozenset(
    {
        const.PROVIDER_OPENAI,
        const.PROVIDER_GROQ,
        const.PROVIDER_DEEPSEEK,
        const.PROVIDER_QWEN,
        const.PROVIDER_OPENROUTER,
    }
)


async def _dispatch_provider(
    provider: str,
    messages: list[dict[str, typing.Any]],
    tools: list[dict[str, typing.Any]] | None,
    max_tokens: int,
    temperature: float,
) -> ChatResponse | None:
    """Route to the correct provider implementation."""
    if provider in _OPENAI_COMPATIBLE:
        endpoint = ai_client.get_openai_endpoint(provider)
        if endpoint is None:
            logger.warning("%s API key not configured", provider)
            return None
        return await _openai_chat_complete(endpoint, messages, tools, max_tokens, temperature)

    if provider == const.PROVIDER_GEMINI:
        return await _gemini_chat_complete(messages, tools, max_tokens, temperature)

    if provider == const.PROVIDER_ANTHROPIC:
        return await _anthropic_chat_complete(messages, tools, max_tokens, temperature)

    logger.error("Unknown chat provider: %s", provider)
    return None


async def _call_with_retry(
    provider: str,
    messages: list[dict[str, typing.Any]],
    tools: list[dict[str, typing.Any]] | None,
    max_tokens: int,
    temperature: float,
) -> ChatResponse | None:
    """Call provider with exponential backoff retry on 429 and 5xx."""
    for attempt in range(_MAX_RETRIES):
        try:
            return await _dispatch_provider(provider, messages, tools, max_tokens, temperature)
        except RateLimitError:
            logger.warning(
                "Chat provider %s rate limited, attempt %d/%d",
                provider,
                attempt + 1,
                _MAX_RETRIES,
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAYS[attempt])
            else:
                raise
        except _ServerError:
            logger.warning(
                "Chat provider %s server error, attempt %d/%d",
                provider,
                attempt + 1,
                _MAX_RETRIES,
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAYS[attempt])
        except httpx.HTTPError as exc:
            logger.error("Chat provider %s request failed: %s", provider, exc)
            return None
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def chat_complete(
    chain: list[str],
    messages: list[dict[str, typing.Any]],
    tools: list[dict[str, typing.Any]] | None = None,
    max_tokens: int = const.GPT_CHAT_MAX_TOKENS,
    temperature: float = const.GPT_CHAT_TEMPERATURE,
) -> ChatResponse | None:
    """Try each provider in chain, falling back on rate limit exhaustion.

    PII is masked out of the whole history before it leaves for any provider (152-ФЗ) and
    restored in the reply, as `ai_client._ai_complete` does for one prompt.

    Returns the first successful ChatResponse, or None if all fail.
    """
    masker = _mask.Masker()
    outgoing = _mask.mask_messages(messages, masker)
    if settings.log_llm_payloads:
        logger.debug("Chat outgoing payload (masked): %s", outgoing)

    for provider in chain:
        try:
            await ai_client.rate_limiter.acquire(provider)
            logger.debug("Using chat provider %s", provider)
            result = await _call_with_retry(provider, outgoing, tools, max_tokens, temperature)
        except RateLimitError:
            logger.warning("Chat provider %s exhausted, falling back to next", provider)
            continue

        if result is not None:
            return _unmasked(result, masker.mapping)

    logger.error("All chat providers in chain exhausted or failed")
    return None


def _unmasked(response: ChatResponse, mapping: dict[str, str]) -> ChatResponse:
    """The reply in the user's words: its text, its tool calls, and the message kept for history."""
    return ChatResponse(
        content=None if response.content is None else _mask.unmask(response.content, mapping),
        tool_calls=[
            dataclasses.replace(call, arguments=_mask.unmask(call.arguments, mapping)) for call in response.tool_calls
        ],
        raw_message=_mask.unmask_message(response.raw_message, mapping),
    )
