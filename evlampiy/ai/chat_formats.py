"""The three provider formats of the GPT chat, and the types its replies come back as.

The chat keeps its history in OpenAI's format; Gemini and Anthropic get it converted here,
and every provider's reply is parsed back into a `ChatResponse`. Pure functions: no network,
no settings — `ai_chat` does the calling.
"""

import dataclasses
import json
import logging
import typing
import uuid

logger = logging.getLogger(__name__)


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


def _tool_arguments(function: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """A tool call's arguments as the object Gemini and Anthropic take.

    They come from a model's earlier reply, in OpenAI's format a JSON string that may be cut
    short or not be an object at all. Such a call already failed when it ran (`tool_calling`)
    and its error is the next message, so the history keeps the call with no arguments instead
    of failing the whole request on it.
    """
    arguments = function.get("arguments", "{}")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = None
    if isinstance(arguments, dict):
        return arguments
    logger.warning("Tool call %s has arguments that are not a JSON object; sending none", function.get("name", ""))
    return {}


def messages_to_gemini(
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
                parts.append({"functionCall": {"name": fn.get("name", ""), "args": _tool_arguments(fn)}})
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


def messages_to_anthropic(
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
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": fn.get("name", ""),
                        "input": _tool_arguments(fn),
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


def parse_openai_response(data: dict[str, typing.Any]) -> ChatResponse:
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
    if raw_tool_calls:
        raw_message["tool_calls"] = raw_tool_calls

    return ChatResponse(content=content, tool_calls=tool_calls, raw_message=raw_message)


def parse_gemini_response(data: dict[str, typing.Any]) -> ChatResponse | None:
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


def parse_anthropic_response(data: dict[str, typing.Any]) -> ChatResponse:
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
