from unittest.mock import MagicMock

import pytest
from telegram.constants import ParseMode

from telegram import InlineKeyboardMarkup

from src.telegram.bot import MAX_TELEGRAM_MESSAGE_LENGTH, send_response

pytestmark = [pytest.mark.asyncio]


class TestSendResponse:
    """Test send_response function."""

    async def test_short_message_sent_as_single_chunk(self, mock_private_update, mock_context):
        """Short message should be sent as single message."""
        await send_response(mock_private_update, mock_context, response="Hello world")

        mock_context.bot.send_message.assert_called_once()
        call_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert call_kwargs["text"] == "Hello world"
        assert call_kwargs["parse_mode"] == ParseMode.HTML
        assert call_kwargs["disable_web_page_preview"] is True

    async def test_long_message_split_into_chunks(self, mock_private_update, mock_context):
        """Long message should be split into multiple chunks."""
        long_text = "A" * (MAX_TELEGRAM_MESSAGE_LENGTH + 100)

        await send_response(mock_private_update, mock_context, response=long_text)

        assert mock_context.bot.send_message.call_count == 2
        first_call = mock_context.bot.send_message.call_args_list[0]
        second_call = mock_context.bot.send_message.call_args_list[1]
        assert len(first_call.kwargs["text"]) == MAX_TELEGRAM_MESSAGE_LENGTH
        assert len(second_call.kwargs["text"]) == 100

    async def test_keyboard_only_on_first_chunk(self, mock_private_update, mock_context):
        """Keyboard should only be attached to the first chunk."""
        long_text = "B" * (MAX_TELEGRAM_MESSAGE_LENGTH * 2 + 50)
        keyboard = MagicMock(spec=InlineKeyboardMarkup)

        await send_response(
            mock_private_update, mock_context, response=long_text, keyboard=keyboard
        )

        assert mock_context.bot.send_message.call_count == 3
        first_call = mock_context.bot.send_message.call_args_list[0]
        second_call = mock_context.bot.send_message.call_args_list[1]
        third_call = mock_context.bot.send_message.call_args_list[2]

        assert first_call.kwargs["reply_markup"] == keyboard
        assert second_call.kwargs["reply_markup"] is None
        assert third_call.kwargs["reply_markup"] is None

    async def test_extra_kwargs_passed_through(self, mock_private_update, mock_context):
        """Extra kwargs should be passed to send_message."""
        await send_response(
            mock_private_update,
            mock_context,
            response="Test",
            reply_to_message_id=42,
        )

        call_kwargs = mock_context.bot.send_message.call_args.kwargs
        assert call_kwargs["reply_to_message_id"] == 42

    async def test_empty_message_not_sent(self, mock_private_update, mock_context):
        """Empty message produces no chunks, nothing is sent."""
        await send_response(mock_private_update, mock_context, response="")

        mock_context.bot.send_message.assert_not_called()

    async def test_exact_max_length_message(self, mock_private_update, mock_context):
        """Message exactly at max length should be single chunk."""
        exact_text = "C" * MAX_TELEGRAM_MESSAGE_LENGTH

        await send_response(mock_private_update, mock_context, response=exact_text)

        mock_context.bot.send_message.assert_called_once()
