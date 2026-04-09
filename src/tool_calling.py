"""Tool-calling conversation loop for GPT chat."""

import json
import logging
import typing

from src import const
from src.ai_chat import ChatResponse, chat_complete
from src.tools import ToolDef

logger = logging.getLogger(__name__)


def _tools_to_schemas(tools: list[ToolDef]) -> list[dict[str, typing.Any]]:
    """Convert ToolDef list to neutral tool schema dicts."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        }
        for t in tools
    ]


async def _execute_tool_call(
    tool_call_name: str,
    tool_call_arguments: str,
    tool_registry: dict[str, ToolDef],
) -> str:
    """Execute a single tool call and return the result string."""
    tool = tool_registry.get(tool_call_name)
    if tool is None:
        return f"Error: unknown tool '{tool_call_name}'"

    try:
        args = json.loads(tool_call_arguments) if tool_call_arguments else {}
        return await tool.handler(**args)
    except Exception as exc:
        logger.exception("Tool %s execution failed", tool_call_name)
        return f"Error executing {tool_call_name}: {exc}"


async def run_tool_conversation(
    messages: list[dict[str, typing.Any]],
    tools: list[ToolDef],
    chain: list[str],
    max_tokens: int = const.GPT_CHAT_MAX_TOKENS,
    temperature: float = const.GPT_CHAT_TEMPERATURE,
) -> str | None:
    """Run a tool-calling conversation loop.

    Sends messages + tool schemas to the LLM. If the LLM returns tool_calls,
    executes each tool, appends results, and re-sends. Repeats until the LLM
    returns content without tool_calls, or max iterations is reached.
    """
    tool_schemas = _tools_to_schemas(tools) if tools else None
    tool_registry = {t.name: t for t in tools}
    last_content: str | None = None

    for iteration in range(const.GPT_MAX_TOOL_ITERATIONS):
        response: ChatResponse | None = await chat_complete(
            chain, messages, tools=tool_schemas, max_tokens=max_tokens, temperature=temperature
        )

        if response is None:
            logger.error("Chat completion returned None at iteration %d", iteration)
            return last_content

        last_content = response.content
        messages.append(response.raw_message)

        if not response.tool_calls:
            return response.content

        logger.debug(
            "Tool calls at iteration %d: %s",
            iteration,
            [tc.name for tc in response.tool_calls],
        )

        for tool_call in response.tool_calls:
            result = await _execute_tool_call(tool_call.name, tool_call.arguments, tool_registry)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.name,
                    "content": result,
                }
            )

    logger.warning("Max tool iterations (%d) reached", const.GPT_MAX_TOOL_ITERATIONS)
    return last_content
