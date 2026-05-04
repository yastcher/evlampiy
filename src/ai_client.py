"""Unified AI provider client for text generation."""

import asyncio
import http
import logging
import typing

import httpx

from src import const
from src.config import settings
from src.mongo import get_bot_config

logger = logging.getLogger(__name__)

# Requests per minute limits for free-tier providers
_PROVIDER_LIMITS: dict[str, int] = {
    const.PROVIDER_GEMINI: 15,
    const.PROVIDER_GROQ: 30,
    const.PROVIDER_OPENROUTER: 10,
    const.PROVIDER_QWEN: 60,
    const.PROVIDER_DEEPSEEK: 60,
}

# Fallback chains: order in which providers are tried on rate limit exhaustion
CATEGORIZATION_FALLBACK_CHAIN: list[str] = [
    const.PROVIDER_DEEPSEEK,
    const.PROVIDER_OPENROUTER,
    const.PROVIDER_GEMINI,
    const.PROVIDER_GROQ,
]
GPT_FALLBACK_CHAIN: list[str] = [
    const.PROVIDER_DEEPSEEK,
    const.PROVIDER_OPENROUTER,
    const.PROVIDER_GEMINI,
    const.PROVIDER_GROQ,
]

_MAX_RETRIES = 3
_RETRY_DELAYS = (2.0, 4.0, 8.0)


class RateLimitError(Exception):
    """Raised when a provider's rate limit is exhausted after all retries."""

    def __init__(self, provider: str, retry_after: float | None = None) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(f"Rate limit exhausted for provider {provider}")


class _ServerError(Exception):
    """Internal: server-side error (5xx), eligible for retry."""


class RateLimiter:
    """Token bucket rate limiter for AI provider requests."""

    def __init__(self, limits: dict[str, int]) -> None:
        self._limits = limits
        self._tokens: dict[str, float] = {p: float(rpm) for p, rpm in limits.items()}
        self._last_check: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {p: asyncio.Lock() for p in limits}

    async def acquire(self, provider: str) -> None:
        """Wait until a request slot is available for provider."""
        if provider not in self._limits:
            return

        rpm = self._limits[provider]
        rate = rpm / 60.0  # tokens per second
        lock = self._locks[provider]

        async with lock:
            now = asyncio.get_event_loop().time()

            if provider in self._last_check:
                elapsed = now - self._last_check[provider]
                self._tokens[provider] = min(float(rpm), self._tokens[provider] + elapsed * rate)
            self._last_check[provider] = now

            if self._tokens[provider] < 1.0:
                wait = (1.0 - self._tokens[provider]) / rate
                await asyncio.sleep(wait)
                self._last_check[provider] = asyncio.get_event_loop().time()
                self._tokens[provider] = 0.0
            else:
                self._tokens[provider] -= 1.0


# Module-level singleton — one rate limiter per process
rate_limiter = RateLimiter(_PROVIDER_LIMITS)


class _HttpClientHolder:
    """Holder for the shared HTTP client — avoids ``global`` keyword."""

    client: httpx.AsyncClient | None = None


_http_holder = _HttpClientHolder()


async def get_http_client() -> httpx.AsyncClient:
    if _http_holder.client is None or _http_holder.client.is_closed:
        # read=45 to allow reasoning models to think, but not stall the chain forever
        _http_holder.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=45.0, write=10.0, pool=5.0)
        )
    return _http_holder.client


async def close_client() -> None:
    """Close the shared HTTP client. Call on application shutdown."""
    if _http_holder.client is not None and not _http_holder.client.is_closed:
        await _http_holder.client.aclose()
        _http_holder.client = None


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
            # Disable thinking for current tasks (cleanup/categorize/tool-calling are
            # formatting jobs, not reasoning). Without this, gemini-2.5-* spends most of
            # maxOutputTokens on hidden thinking tokens and truncates the visible answer.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = f"{const.GEMINI_API_BASE}/v1beta/models/{settings.gemini_model}:generateContent"

    client = await get_http_client()
    response = await client.post(url, headers=headers, json=payload)

    if response.status_code == http.HTTPStatus.OK:
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            logger.error("Gemini returned empty candidates")
            return None
        finish_reason = candidates[0].get("finishReason")
        if finish_reason and finish_reason != "STOP":
            logger.warning("Gemini finishReason=%s (response may be truncated)", finish_reason)
        return str(candidates[0]["content"]["parts"][0]["text"])

    if response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
        raise RateLimitError(const.PROVIDER_GEMINI)

    if response.status_code >= _HTTP_5XX_MIN:
        raise _ServerError(f"Gemini server error: {response.status_code}")

    logger.error("Gemini API error, status: %s, body: %.300s", response.status_code, response.text)
    return None


async def _anthropic_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call Anthropic Messages API."""
    if not settings.anthropic_bot_api_key:
        logger.warning("Anthropic API key not configured")
        return None

    headers = {
        "x-api-key": settings.anthropic_bot_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    client = await get_http_client()
    response = await client.post(
        f"{const.ANTHROPIC_API_BASE}/v1/messages",
        headers=headers,
        json=payload,
    )

    if response.status_code == http.HTTPStatus.OK:
        data = response.json()
        return str(data["content"][0]["text"])

    if response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
        raise RateLimitError(const.PROVIDER_ANTHROPIC)

    if response.status_code >= _HTTP_5XX_MIN:
        raise _ServerError(f"Anthropic server error: {response.status_code}")

    logger.error("Anthropic API error, status: %s", response.status_code)
    return None


async def _openai_format_complete(
    endpoint: OpenAIEndpoint, prompt: str, max_tokens: int, temperature: float
) -> str | None:
    """Call an OpenAI-compatible Chat Completions API."""
    headers = {
        "authorization": f"Bearer {endpoint.api_key}",
        "content-type": "application/json",
    }
    payload = {
        "model": endpoint.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    client = await get_http_client()
    response = await client.post(endpoint.url, headers=headers, json=payload)

    if response.status_code == http.HTTPStatus.OK:
        data = response.json()
        return str(data["choices"][0]["message"]["content"])

    if response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
        raise RateLimitError(endpoint.provider)

    if response.status_code >= _HTTP_5XX_MIN:
        raise _ServerError(f"{endpoint.provider} server error: {response.status_code}")

    logger.error(
        "%s API error, status: %s, body: %.300s",
        endpoint.provider,
        response.status_code,
        response.text,
    )
    return None


async def _openai_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call OpenAI Chat Completions API."""
    if not settings.gpt_token:
        logger.warning("OpenAI API key not configured")
        return None

    endpoint = OpenAIEndpoint(
        provider=const.PROVIDER_OPENAI,
        url=f"{const.OPENAI_API_BASE}/v1/chat/completions",
        api_key=settings.gpt_token,
        model=settings.gpt_model,
    )
    return await _openai_format_complete(endpoint, prompt, max_tokens, temperature)


async def _groq_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call Groq LLM API (OpenAI-compatible)."""
    if not settings.groq_api_key:
        logger.warning("Groq API key not configured")
        return None

    endpoint = OpenAIEndpoint(
        provider=const.PROVIDER_GROQ,
        url=f"{const.GROQ_API_BASE}/openai/v1/chat/completions",
        api_key=settings.groq_api_key,
        model=settings.groq_llm_model,
    )
    return await _openai_format_complete(endpoint, prompt, max_tokens, temperature)


async def _deepseek_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call DeepSeek API (OpenAI-compatible)."""
    if not settings.deepseek_api_key:
        logger.warning("DeepSeek API key not configured")
        return None

    endpoint = OpenAIEndpoint(
        provider=const.PROVIDER_DEEPSEEK,
        url=f"{const.DEEPSEEK_API_BASE}/chat/completions",
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
    )
    return await _openai_format_complete(endpoint, prompt, max_tokens, temperature)


async def _qwen_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call Alibaba Qwen API (OpenAI-compatible, international endpoint)."""
    if not settings.qwen_api_key:
        logger.warning("Qwen API key not configured")
        return None

    endpoint = OpenAIEndpoint(
        provider=const.PROVIDER_QWEN,
        url=f"{const.QWEN_API_BASE}/chat/completions",
        api_key=settings.qwen_api_key,
        model=settings.qwen_model,
    )
    return await _openai_format_complete(endpoint, prompt, max_tokens, temperature)


async def _openrouter_complete(prompt: str, max_tokens: int, temperature: float) -> str | None:
    """Call OpenRouter API (OpenAI-compatible)."""
    if not settings.openrouter_api_key:
        logger.warning("OpenRouter API key not configured")
        return None

    endpoint = OpenAIEndpoint(
        provider=const.PROVIDER_OPENROUTER,
        url=f"{const.OPENROUTER_API_BASE}/api/v1/chat/completions",
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model,
    )
    return await _openai_format_complete(endpoint, prompt, max_tokens, temperature)


_HTTP_5XX_MIN = http.HTTPStatus.INTERNAL_SERVER_ERROR  # >= 500 means server error

_ProviderFn = typing.Callable[
    [str, int, float], typing.Coroutine[typing.Any, typing.Any, str | None]
]


class OpenAIEndpoint(typing.NamedTuple):
    """Groups the fixed params for an OpenAI-compatible API endpoint."""

    provider: str
    url: str
    api_key: str
    model: str


_OPENAI_ENDPOINTS: dict[str, typing.Callable[[], OpenAIEndpoint | None]] = {
    const.PROVIDER_OPENAI: lambda: (
        OpenAIEndpoint(
            const.PROVIDER_OPENAI,
            f"{const.OPENAI_API_BASE}/v1/chat/completions",
            settings.gpt_token,
            settings.gpt_model,
        )
        if settings.gpt_token
        else None
    ),
    const.PROVIDER_GROQ: lambda: (
        OpenAIEndpoint(
            const.PROVIDER_GROQ,
            f"{const.GROQ_API_BASE}/openai/v1/chat/completions",
            settings.groq_api_key,
            settings.groq_llm_model,
        )
        if settings.groq_api_key
        else None
    ),
    const.PROVIDER_DEEPSEEK: lambda: (
        OpenAIEndpoint(
            const.PROVIDER_DEEPSEEK,
            f"{const.DEEPSEEK_API_BASE}/chat/completions",
            settings.deepseek_api_key,
            settings.deepseek_model,
        )
        if settings.deepseek_api_key
        else None
    ),
    const.PROVIDER_QWEN: lambda: (
        OpenAIEndpoint(
            const.PROVIDER_QWEN,
            f"{const.QWEN_API_BASE}/chat/completions",
            settings.qwen_api_key,
            settings.qwen_model,
        )
        if settings.qwen_api_key
        else None
    ),
    const.PROVIDER_OPENROUTER: lambda: (
        OpenAIEndpoint(
            const.PROVIDER_OPENROUTER,
            f"{const.OPENROUTER_API_BASE}/api/v1/chat/completions",
            settings.openrouter_api_key,
            settings.openrouter_model,
        )
        if settings.openrouter_api_key
        else None
    ),
}


def get_openai_endpoint(provider: str) -> OpenAIEndpoint | None:
    """Build an OpenAIEndpoint for the named provider, or None if API key is missing."""
    factory = _OPENAI_ENDPOINTS.get(provider)
    if factory is None:
        return None
    return factory()


_PROVIDERS: dict[str, _ProviderFn] = {
    const.PROVIDER_GEMINI: _gemini_complete,
    const.PROVIDER_ANTHROPIC: _anthropic_complete,
    const.PROVIDER_OPENAI: _openai_complete,
    const.PROVIDER_GROQ: _groq_complete,
    const.PROVIDER_OPENROUTER: _openrouter_complete,
    const.PROVIDER_QWEN: _qwen_complete,
    const.PROVIDER_DEEPSEEK: _deepseek_complete,
}


async def _call_with_retry(
    provider: str,
    handler: _ProviderFn,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> str | None:
    """Call provider with exponential backoff retry on 429 and 5xx."""
    for attempt in range(_MAX_RETRIES):
        try:
            return await handler(prompt, max_tokens, temperature)
        except RateLimitError:
            logger.warning(
                "Provider %s rate limited, attempt %d/%d",
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
                "Provider %s server error, attempt %d/%d",
                provider,
                attempt + 1,
                _MAX_RETRIES,
            )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAYS[attempt])
        except httpx.HTTPError as exc:
            logger.error("Provider %s request failed: %s", provider, exc)
            return None
    return None


async def _ai_complete(
    chain: list[str], prompt: str, max_tokens: int, temperature: float
) -> str | None:
    """Try each provider in chain, falling back on rate limit exhaustion."""
    for provider in chain:
        handler = _PROVIDERS.get(provider)
        if not handler:
            logger.error("Unknown AI provider: %s", provider)
            continue

        try:
            await rate_limiter.acquire(provider)
            logger.debug("Using provider %s", provider)
            raw = await _call_with_retry(provider, handler, prompt, max_tokens, temperature)
        except RateLimitError:
            logger.warning("Provider %s exhausted, falling back to next", provider)
            continue

        if raw is not None:
            result = _strip_backticks(raw)
            if result:
                return result
            logger.warning("Provider %s returned empty response, trying next", provider)

    logger.error("All providers in chain exhausted or failed")
    return None


async def classify_text(prompt: str) -> str | None:
    """Classify text using the configured categorization provider with fallback."""
    primary = await get_bot_config("categorization_provider", settings.categorization_provider)
    chain = [primary] + [p for p in CATEGORIZATION_FALLBACK_CHAIN if p != primary]
    return await _ai_complete(chain, prompt, max_tokens=const.CLASSIFY_MAX_TOKENS, temperature=0.0)


async def cleanup_text(prompt: str, max_tokens: int) -> str | None:
    """Clean up text using the configured GPT provider with fallback."""
    primary = await get_bot_config("gpt_provider", settings.gpt_provider)
    chain = [primary] + [p for p in GPT_FALLBACK_CHAIN if p != primary]
    return await _ai_complete(chain, prompt, max_tokens=max_tokens, temperature=0.0)


async def gpt_chat(prompt: str) -> str | None:
    """Generate a chat response using the configured GPT provider with fallback."""
    primary = await get_bot_config("gpt_provider", settings.gpt_provider)
    chain = [primary] + [p for p in GPT_FALLBACK_CHAIN if p != primary]
    return await _ai_complete(
        chain, prompt, max_tokens=const.GPT_CHAT_MAX_TOKENS, temperature=const.GPT_CHAT_TEMPERATURE
    )
