"""Tests for the tool-calling conversation loop."""

from unittest.mock import AsyncMock, patch

from src.ai_chat import ChatResponse, ToolCall
from src.tool_calling import run_tool_conversation
from src.tools import ToolDef


def _make_tool(name: str = "test_tool", result: str = "tool_result") -> ToolDef:
    """Create a simple test tool."""

    async def handler(**kwargs: object) -> str:
        return result

    return ToolDef(
        name=name,
        description="A test tool",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=handler,
    )


def _text_response(content: str) -> ChatResponse:
    """Create a ChatResponse with just text content."""
    return ChatResponse(
        content=content,
        tool_calls=[],
        raw_message={"role": "assistant", "content": content},
    )


def _tool_call_response(name: str, arguments: str = "{}", call_id: str = "call_1") -> ChatResponse:
    """Create a ChatResponse with a tool call."""
    return ChatResponse(
        content=None,
        tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
        raw_message={
            "role": "assistant",
            "tool_calls": [{"id": call_id, "function": {"name": name, "arguments": arguments}}],
        },
    )


class TestNoToolCalls:
    """Test when LLM responds without tool calls."""

    async def test_returns_content_directly(self):
        mock_complete = AsyncMock(return_value=_text_response("Hello!"))
        messages = [{"role": "user", "content": "Hi"}]

        with patch("src.tool_calling.chat_complete", mock_complete):
            result = await run_tool_conversation(messages, [], ["deepseek"])

        assert result == "Hello!"

    async def test_returns_none_when_provider_fails(self):
        mock_complete = AsyncMock(return_value=None)
        messages = [{"role": "user", "content": "Hi"}]

        with patch("src.tool_calling.chat_complete", mock_complete):
            result = await run_tool_conversation(messages, [], ["deepseek"])

        assert result is None


class TestSingleToolCall:
    """Test single tool call round-trip."""

    async def test_executes_tool_and_returns_final_answer(self):
        tool = _make_tool("get_notes", '{"notes": ["note1"]}')

        mock_complete = AsyncMock(
            side_effect=[
                _tool_call_response("get_notes"),
                _text_response("Here are your notes: note1"),
            ]
        )

        messages = [{"role": "user", "content": "Show notes"}]

        with patch("src.tool_calling.chat_complete", mock_complete):
            result = await run_tool_conversation(messages, [tool], ["deepseek"])

        assert result == "Here are your notes: note1"
        assert mock_complete.call_count == 2

    async def test_tool_result_added_to_messages(self):
        tool = _make_tool("get_notes", "notes_data")

        captured_messages = []

        async def capture_complete(chain, messages, **kwargs):
            captured_messages.append([m.copy() for m in messages])
            if len(captured_messages) == 1:
                return _tool_call_response("get_notes")
            return _text_response("Done")

        messages = [{"role": "user", "content": "Show notes"}]

        with patch("src.tool_calling.chat_complete", side_effect=capture_complete):
            await run_tool_conversation(messages, [tool], ["deepseek"])

        # Second call should include tool result
        second_call_msgs = captured_messages[1]
        tool_msg = next(m for m in second_call_msgs if m.get("role") == "tool")
        assert tool_msg["content"] == "notes_data"
        assert tool_msg["name"] == "get_notes"

    async def test_passes_arguments_to_tool(self):
        received_args: dict[str, object] = {}

        async def handler(**kwargs: object) -> str:
            received_args.update(kwargs)
            return "ok"

        tool = ToolDef(
            name="get_notes",
            description="Get notes",
            parameters={
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
                "required": [],
            },
            handler=handler,
        )

        mock_complete = AsyncMock(
            side_effect=[
                _tool_call_response("get_notes", '{"limit": 5}'),
                _text_response("Done"),
            ]
        )

        with patch("src.tool_calling.chat_complete", mock_complete):
            await run_tool_conversation(
                [{"role": "user", "content": "notes"}], [tool], ["deepseek"]
            )

        assert received_args == {"limit": 5}


class TestMultipleToolCalls:
    """Test multiple tool calls in one turn."""

    async def test_executes_all_tool_calls(self):
        tool_a = _make_tool("tool_a", "result_a")
        tool_b = _make_tool("tool_b", "result_b")

        two_calls = ChatResponse(
            content=None,
            tool_calls=[
                ToolCall(id="c1", name="tool_a", arguments="{}"),
                ToolCall(id="c2", name="tool_b", arguments="{}"),
            ],
            raw_message={
                "role": "assistant",
                "tool_calls": [
                    {"id": "c1", "function": {"name": "tool_a", "arguments": "{}"}},
                    {"id": "c2", "function": {"name": "tool_b", "arguments": "{}"}},
                ],
            },
        )

        mock_complete = AsyncMock(side_effect=[two_calls, _text_response("Combined result")])

        with patch("src.tool_calling.chat_complete", mock_complete):
            result = await run_tool_conversation(
                [{"role": "user", "content": "both"}], [tool_a, tool_b], ["deepseek"]
            )

        assert result == "Combined result"


class TestErrorHandling:
    """Test error handling in tool execution."""

    async def test_unknown_tool_sends_error_to_llm(self):
        mock_complete = AsyncMock(
            side_effect=[
                _tool_call_response("nonexistent"),
                _text_response("Sorry, could not find that tool"),
            ]
        )

        with patch("src.tool_calling.chat_complete", mock_complete):
            result = await run_tool_conversation(
                [{"role": "user", "content": "test"}], [], ["deepseek"]
            )

        assert result == "Sorry, could not find that tool"

    async def test_tool_exception_sends_error_to_llm(self):
        async def failing_handler(**kwargs: object) -> str:
            msg = "DB connection failed"
            raise RuntimeError(msg)

        tool = ToolDef(
            name="broken",
            description="Broken tool",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=failing_handler,
        )

        captured_messages = []

        async def capture_complete(chain, messages, **kwargs):
            captured_messages.append([m.copy() for m in messages])
            if len(captured_messages) == 1:
                return _tool_call_response("broken")
            return _text_response("Tool error occurred")

        with patch("src.tool_calling.chat_complete", side_effect=capture_complete):
            result = await run_tool_conversation(
                [{"role": "user", "content": "test"}], [tool], ["deepseek"]
            )

        assert result == "Tool error occurred"
        tool_result = next(m for m in captured_messages[1] if m.get("role") == "tool")
        assert "Error executing broken" in tool_result["content"]


class TestMaxIterations:
    """Test safety limit on tool calling iterations."""

    async def test_stops_at_max_iterations(self):
        tool = _make_tool("loopy", "loop_result")

        # Always returns a tool call, never a final answer
        mock_complete = AsyncMock(
            return_value=_tool_call_response("loopy"),
        )

        with patch("src.tool_calling.chat_complete", mock_complete):
            result = await run_tool_conversation(
                [{"role": "user", "content": "loop"}], [tool], ["deepseek"]
            )

        # Should stop at GPT_MAX_TOOL_ITERATIONS (5)
        assert mock_complete.call_count == 5
        # Returns last content (None in this case since tool calls have no content)
        assert result is None
