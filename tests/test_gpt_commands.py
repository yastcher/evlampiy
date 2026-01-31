from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.gpt_commands import evlampiy_command

pytestmark = [pytest.mark.asyncio]


class TestEvlampiyCommand:
    """Test GPT command handler."""

    async def test_sends_gpt_response(self, mock_private_update, mock_context):
        """GPT response is sent to user."""
        mock_private_update.message.text = "Tell me a joke"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Why did the chicken..."))]

        with (
            patch("src.gpt_commands.client.chat.completions.create") as mock_create,
            patch("src.gpt_commands.send_response", AsyncMock()) as mock_send,
        ):
            mock_create.return_value = mock_response

            await evlampiy_command(mock_private_update, mock_context)

            mock_create.assert_called_once()
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["response"] == "Why did the chicken..."

    async def test_handles_api_error(self, mock_private_update, mock_context):
        """API errors are caught and sent to user."""
        mock_private_update.message.text = "Test"

        with (
            patch("src.gpt_commands.client.chat.completions.create") as mock_create,
            patch("src.gpt_commands.send_response", AsyncMock()) as mock_send,
        ):
            mock_create.side_effect = Exception("API Error")

            await evlampiy_command(mock_private_update, mock_context)

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert "API Error" in call_kwargs["response"]

    async def test_uses_correct_model(self, mock_private_update, mock_context):
        """Uses model from settings."""
        mock_private_update.message.text = "Test"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]

        with (
            patch("src.gpt_commands.client.chat.completions.create") as mock_create,
            patch("src.gpt_commands.send_response", AsyncMock()),
            patch("src.gpt_commands.settings.gpt_model", "gpt-4"),
        ):
            mock_create.return_value = mock_response

            await evlampiy_command(mock_private_update, mock_context)

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["model"] == "gpt-4"
