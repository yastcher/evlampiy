from unittest.mock import AsyncMock, patch

from src.gpt_commands import evlampiy_command


class TestEvlampiyCommand:
    """Test GPT command handler (Trophy: real send_response, mock only AI boundary)."""

    async def test_sends_gpt_response(self, mock_private_update, mock_context):
        """AI response is sent to user via real send_response path."""
        mock_private_update.message.text = "Tell me a joke"

        with patch(
            "src.gpt_commands.run_tool_conversation",
            AsyncMock(return_value="Why did the chicken..."),
        ):
            await evlampiy_command(mock_private_update, mock_context)

        mock_context.bot.send_message.assert_called_once()
        call_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert call_kwargs["text"] == "Why did the chicken..."

    async def test_handles_api_error(self, mock_private_update, mock_context):
        """API errors are caught and sent to user."""
        mock_private_update.message.text = "Test"

        with patch(
            "src.gpt_commands.run_tool_conversation",
            AsyncMock(side_effect=Exception("API Error")),
        ):
            await evlampiy_command(mock_private_update, mock_context)

        mock_context.bot.send_message.assert_called_once()
        call_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert "API Error" in call_kwargs["text"]

    async def test_handles_empty_response(self, mock_private_update, mock_context):
        """Handles None response from AI."""
        mock_private_update.message.text = "Test"

        with patch(
            "src.gpt_commands.run_tool_conversation",
            AsyncMock(return_value=None),
        ):
            await evlampiy_command(mock_private_update, mock_context)

        mock_context.bot.send_message.assert_called_once()
        call_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert "Empty response" in call_kwargs["text"]

    async def test_builds_messages_with_system_prompt(self, mock_private_update, mock_context):
        """System prompt and user message are passed to run_tool_conversation."""
        mock_private_update.message.text = "What are my notes?"
        mock_conv = AsyncMock(return_value="Your notes are...")

        with patch("src.gpt_commands.run_tool_conversation", mock_conv):
            await evlampiy_command(mock_private_update, mock_context)

        call_args = mock_conv.call_args
        messages = call_args[0][0]  # first positional arg
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What are my notes?"

    async def test_passes_tools(self, mock_private_update, mock_context):
        """Tools list is passed to run_tool_conversation."""
        mock_private_update.message.text = "Test"
        mock_conv = AsyncMock(return_value="ok")

        with patch("src.gpt_commands.run_tool_conversation", mock_conv):
            await evlampiy_command(mock_private_update, mock_context)

        call_args = mock_conv.call_args
        tools = call_args[0][1]  # second positional arg
        tool_names = [t.name for t in tools]
        assert "get_recent_notes" in tool_names
        assert "get_user_settings" in tool_names
        assert "get_categories" in tool_names

    async def test_skips_when_no_message(self, mock_private_update, mock_context):
        """Does nothing when update.message is None."""
        mock_private_update.message = None

        with patch("src.gpt_commands.run_tool_conversation", AsyncMock()) as mock_conv:
            await evlampiy_command(mock_private_update, mock_context)

        mock_conv.assert_not_called()
