from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import InlineKeyboardMarkup

from src.telegram import setup as bot_setup
from src.telegram.bot import MAX_TELEGRAM_MESSAGE_LENGTH, send_response


class TestSendResponse:
    """Test send_response function."""

    async def test_short_message_sent_as_single_chunk(self, mock_private_update, mock_context):
        """Short message should be sent as single message."""
        await send_response(mock_private_update, mock_context, response="Hello world")

        mock_context.send_message.assert_called_once()
        call_kwargs = mock_context.send_message.call_args.kwargs
        assert call_kwargs["text"] == "Hello world"
        assert call_kwargs["parse_mode"] == ParseMode.HTML
        assert call_kwargs["link_preview_options"].is_disabled is True

    async def test_long_message_split_into_chunks(self, mock_private_update, mock_context):
        """Long message should be split into multiple chunks."""
        long_text = "A" * (MAX_TELEGRAM_MESSAGE_LENGTH + 100)

        await send_response(mock_private_update, mock_context, response=long_text)

        assert mock_context.send_message.call_count == 2
        first_call = mock_context.send_message.call_args_list[0]
        second_call = mock_context.send_message.call_args_list[1]
        assert len(first_call.kwargs["text"]) == MAX_TELEGRAM_MESSAGE_LENGTH
        assert len(second_call.kwargs["text"]) == 100

    async def test_keyboard_only_on_first_chunk(self, mock_private_update, mock_context):
        """Keyboard should only be attached to the first chunk."""
        long_text = "B" * (MAX_TELEGRAM_MESSAGE_LENGTH * 2 + 50)
        keyboard = MagicMock(spec=InlineKeyboardMarkup)

        await send_response(mock_private_update, mock_context, response=long_text, keyboard=keyboard)

        assert mock_context.send_message.call_count == 3
        first_call = mock_context.send_message.call_args_list[0]
        second_call = mock_context.send_message.call_args_list[1]
        third_call = mock_context.send_message.call_args_list[2]

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

        call_kwargs = mock_context.send_message.call_args.kwargs
        assert call_kwargs["reply_to_message_id"] == 42

    async def test_empty_message_not_sent(self, mock_private_update, mock_context):
        """Empty message produces no chunks, nothing is sent."""
        await send_response(mock_private_update, mock_context, response="")

        mock_context.send_message.assert_not_called()

    async def test_exact_max_length_message(self, mock_private_update, mock_context):
        """Message exactly at max length should be single chunk."""
        exact_text = "C" * MAX_TELEGRAM_MESSAGE_LENGTH

        await send_response(mock_private_update, mock_context, response=exact_text)

        mock_context.send_message.assert_called_once()


class TestRunBotResilience:
    """run_bot must not crash when non-critical startup steps fail."""

    async def test_command_registration_network_error_does_not_block_polling(self):
        """A TelegramNetworkError from set_my_commands must not stop polling."""
        bot = AsyncMock()
        dp = AsyncMock()
        boom = TelegramNetworkError(method=MagicMock(), message="timeout")
        with (
            patch.object(bot_setup, "build_bot", return_value=bot),
            patch.object(bot_setup, "build_dispatcher", return_value=dp),
            patch.object(bot_setup, "setup_bot_commands", AsyncMock(side_effect=boom)),
            patch.object(bot_setup, "run_selftest", AsyncMock()),
        ):
            await bot_setup.run_bot()

        dp.start_polling.assert_awaited_once_with(bot)


class TestBuildBot:
    """build_bot wires the optional Telegram API reverse proxy."""

    def test_uses_custom_api_base_when_set(self):
        with patch.object(bot_setup.settings, "telegram_api_base", "https://proxy.workers.dev"):
            bot = bot_setup.build_bot()

        assert "proxy.workers.dev" in bot.session.api.api_url(token="123", method="getMe")

    def test_uses_official_api_by_default(self):
        with patch.object(bot_setup.settings, "telegram_api_base", ""):
            bot = bot_setup.build_bot()

        assert "api.telegram.org" in bot.session.api.api_url(token="123", method="getMe")
