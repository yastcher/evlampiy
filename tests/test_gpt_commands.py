from unittest.mock import AsyncMock, patch

from src.gpt_commands import evlampiy_command


class TestEvlampiyCommand:
    """Test GPT command handler."""

    async def test_sends_gpt_response(self, mock_private_update, mock_context):
        """AI response is sent to user."""
        mock_private_update.message.text = "Tell me a joke"

        with (
            patch("src.gpt_commands.gpt_chat", AsyncMock(return_value="Why did the chicken...")),
            patch("src.gpt_commands.send_response", AsyncMock()) as mock_send,
        ):
            await evlampiy_command(mock_private_update, mock_context)

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["response"] == "Why did the chicken..."

    async def test_handles_api_error(self, mock_private_update, mock_context):
        """API errors are caught and sent to user."""
        mock_private_update.message.text = "Test"

        with (
            patch("src.gpt_commands.gpt_chat", AsyncMock(side_effect=Exception("API Error"))),
            patch("src.gpt_commands.send_response", AsyncMock()) as mock_send,
        ):
            await evlampiy_command(mock_private_update, mock_context)

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert "API Error" in call_kwargs["response"]

    async def test_handles_empty_response(self, mock_private_update, mock_context):
        """Handles None response from AI."""
        mock_private_update.message.text = "Test"

        with (
            patch("src.gpt_commands.gpt_chat", AsyncMock(return_value=None)),
            patch("src.gpt_commands.send_response", AsyncMock()) as mock_send,
        ):
            await evlampiy_command(mock_private_update, mock_context)

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert "Empty response" in call_kwargs["response"]
