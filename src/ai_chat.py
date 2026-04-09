"""Messages-based AI chat completion with tool calling support.

Unlike ai_client.py (prompt-based, returns plain str), this module works with
message lists and structured responses including tool calls. Supports all
provider formats: OpenAI-compatible, Gemini, Anthropic.
"""

import asyncio
import dataclasses
import http
import json
import logging
import typing
import uuid

import httpx

from src import ai_client, const
from src.ai_client import OpenAIEndpoint, RateLimitError
from src.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAYS = (2.0, 4.0, 8.0)
_HTTP_5XX_MIN = http.HTTPStatus.INTERNAL_SERVER_ERROR


@dataclasses.dataclass(frozen=True, slots=True)
class ToolCall:
    """A single tool call requested by the LLM."""

    id: str
    name: str
    arguments: str  # JSON string


@dataclasses.dataclass(frozen=True, slots=True)
class ChatResponse:
    """Structured response from chat completion."""

    content: str | None
    tool_calls: list[ToolCall]
    raw_message: dict[str, typing.Any]  # for re-insertion into message history


# ---------------------------------------------------------------------------
# Schema conversion helpers
# ---------------------------------------------------------------------------


def tools_to_openai(
    tools: list[dict[str, typing.Any]],
) -> list[dict[str, typing.Any]]:
    """Convert neutral tool defs to OpenAI format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools
    ]


def tools_to_gemini(
    tools: list[dict[str, typing.Any]],
) -> list[dict[str, typing.Any]]:
    """Convert neutral tool defs to Gemini function_declarations format."""
    declarations = [
        {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        }
        for t in tools
    ]
    return [{"function_declarations": declarations}]


def tools_to_anthropic(
    tools: list[dict[str, typing.Any]],
) -> list[dict[str, typing.Any]]:
    """Convert neutral tool defs to Anthropic format."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in tools
    ]


# ---------------------------------------------------------------------------
# Message conversion helpers
# ---------------------------------------------------------------------------


def _messages_to_gemini(
    messages: list[dict[str, typing.Any]],
) -> tuple[str | None, list[dict[str, typing.Any]]]:
    """Convert OpenAI-format messages to Gemini contents.

    Returns (system_instruction, contents).
    """
    system_text: str | None = None
    contents: list[dict[str, typing.Any]] = []

    for msg in messages:
        role = msg.get("role", "")

        if role == "system":
            system_text = msg.get("content", "")

        elif role == "assistant":
            parts: list[dict[str, typing.Any]] = []
            if msg.get("content"):
                parts.append({"text": msg["content"]})
            for tc in msg.get("tool_calls", []):
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                parts.append(
                    {
                        "functionCall": {
                            "name": fn.get("name", ""),
                            "args": json.loads(args) if isinstance(args, str) else args,
                        }
                    }
                )
            if parts:
                contents.append({"role": "model", "parts": parts})

        elif role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": msg.get("name", ""),
                                "response": {"result": msg.get("content", "")},
                            }
                        }
                    ],
                }
            )

        else:
            # user
            contents.append({"role": "user", "parts": [{"text": msg.get("content", "")}]})

    return system_text, contents


def _messages_to_anthropic(
    messages: list[dict[str, typing.Any]],
) -> tuple[str | None, list[dict[str, typing.Any]]]:
    """Convert OpenAI-format messages to Anthropic format.

    Returns (system_text, messages).
    """
    system_text: str | None = None
    result: list[dict[str, typing.Any]] = []

    for msg in messages:
        role = msg.get("role", "")

        if role == "system":
            system_text = msg.get("content", "")

        elif role == "assistant":
            content_blocks: list[dict[str, typing.Any]] = []
            if msg.get("content"):
                content_blocks.append({"type": "text", "text": msg["content"]})
            for tc in msg.get("tool_calls", []):
                fn = tc.get("function", {})
                args_str = fn.get("arguments", "{}")
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": fn.get("name", ""),
                        "input": json.loads(args_str) if isinstance(args_str, str) else args_str,
                    }
                )
            result.append({"role": "assistant", "content": content_blocks})

        elif role == "tool":
            result.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.get("tool_call_id", ""),
                            "content": msg.get("content", ""),
                        }
                    ],
                }
            )

        else:
            # user
            result.append({"role": "user", "content": msg.get("content", "")})

    return system_text, result


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


def _parse_openai_response(data: dict[str, typing.Any]) -> ChatResponse:
    """Parse OpenAI-compatible chat completion response."""
    message = data["choices"][0]["message"]
    content = message.get("content")
    raw_tool_calls = message.get("tool_calls") or []

    tool_calls = [
        ToolCall(
            id=tc["id"],
            name=tc["function"]["name"],
            arguments=tc["function"]["arguments"],
        )
        for tc in raw_tool_calls
    ]

    raw_message: dict[str, typing.Any] = {"role": "assistant"}
    if content:
        raw_message["content"] = content
    elif raw_tool_calls:
        raw_message["tool_calls"] = raw_tool_calls

    return ChatResponse(content=content, tool_calls=tool_calls, raw_message=raw_message)


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
        return _parse_openai_response(response.json())

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


def _parse_gemini_response(data: dict[str, typing.Any]) -> ChatResponse | None:
    """Parse Gemini generateContent response."""
    candidates = data.get("candidates", [])
    if not candidates:
        logger.error("Gemini returned empty candidates")
        return None

    parts = candidates[0].get("content", {}).get("parts", [])
    content: str | None = None
    tool_calls: list[ToolCall] = []
    raw_tool_calls: list[dict[str, typing.Any]] = []

    for part in parts:
        if "text" in part:
            content = part["text"]
        if "functionCall" in part:
            fc = part["functionCall"]
            call_id = str(uuid.uuid4())
            tool_calls.append(
                ToolCall(
                    id=call_id,
                    name=fc["name"],
                    arguments=json.dumps(fc.get("args", {})),
                )
            )
            raw_tool_calls.append(
                {
                    "id": call_id,
                    "function": {
                        "name": fc["name"],
                        "arguments": json.dumps(fc.get("args", {})),
                    },
                }
            )

    raw_message: dict[str, typing.Any] = {"role": "assistant"}
    if content:
        raw_message["content"] = content
    if raw_tool_calls:
        raw_message["tool_calls"] = raw_tool_calls

    return ChatResponse(content=content, tool_calls=tool_calls, raw_message=raw_message)


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

    system_text, contents = _messages_to_gemini(messages)

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

    url = f"{const.GEMINI_API_BASE}/v1beta/models/{settings.gemini_model}:generateContent"

    client = await ai_client.get_http_client()
    response = await client.post(url, headers=headers, json=payload)

    if response.status_code == http.HTTPStatus.OK:
        return _parse_gemini_response(response.json())

    if response.status_code == http.HTTPStatus.TOO_MANY_REQUESTS:
        raise RateLimitError(const.PROVIDER_GEMINI)

    if response.status_code >= _HTTP_5XX_MIN:
        raise _ServerError(f"Gemini server error: {response.status_code}")

    logger.error(
        "Gemini chat API error, status: %s, body: %.300s", response.status_code, response.text
    )
    return None


def _parse_anthropic_response(data: dict[str, typing.Any]) -> ChatResponse:
    """Parse Anthropic Messages API response."""
    content_blocks = data.get("content", [])
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    raw_tool_calls: list[dict[str, typing.Any]] = []

    for block in content_blocks:
        if block.get("type") == "text":
            text_parts.append(block["text"])
        elif block.get("type") == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block["id"],
                    name=block["name"],
                    arguments=json.dumps(block.get("input", {})),
                )
            )
            raw_tool_calls.append(
                {
                    "id": block["id"],
                    "function": {
                        "name": block["name"],
                        "arguments": json.dumps(block.get("input", {})),
                    },
                }
            )

    content = "\n".join(text_parts) if text_parts else None

    raw_message: dict[str, typing.Any] = {"role": "assistant"}
    if content:
        raw_message["content"] = content
    if raw_tool_calls:
        raw_message["tool_calls"] = raw_tool_calls

    return ChatResponse(content=content, tool_calls=tool_calls, raw_message=raw_message)


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

    system_text, anthropic_messages = _messages_to_anthropic(messages)

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
        f"{const.ANTHROPIC_API_BASE}/v1/messages",
        headers=headers,
        json=payload,
    )

    if response.status_code == http.HTTPStatus.OK:
        return _parse_anthropic_response(response.json())

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

    Returns the first successful ChatResponse, or None if all fail.
    """
    for provider in chain:
        try:
            await ai_client.rate_limiter.acquire(provider)
            logger.debug("Using chat provider %s", provider)
            result = await _call_with_retry(provider, messages, tools, max_tokens, temperature)
        except RateLimitError:
            logger.warning("Chat provider %s exhausted, falling back to next", provider)
            continue

        if result is not None:
            return result

    logger.error("All chat providers in chain exhausted or failed")
    return None
