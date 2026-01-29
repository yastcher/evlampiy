from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ChatMemberStatus

from src.config import ENGLISH, GERMANY, RUSSIAN, SPANISH
from src.telegram.handlers import choose_language, lang_buttons, start

pytestmark = [pytest.mark.asyncio]


class TestStartCommand:
    """Test /start command in different contexts."""

    async def test_private_chat_new_user(self, mock_private_update, mock_context):
        """New user sends /start in private chat."""
        with (
            patch("src.telegram.handlers.get_chat_language", AsyncMock(return_value="en")),
            patch("src.telegram.handlers.get_gpt_command", AsyncMock(return_value="евлампий")),
        ):
            await start(mock_private_update, mock_context)

            mock_private_update.message.reply_text.assert_called_once()
            reply_text = mock_private_update.message.reply_text.call_args[0][0]
            assert "voice" in reply_text.lower()
            assert "en" in reply_text

    async def test_group_chat_admin_allowed(self, mock_group_update, mock_context):
        """Admin sends /start in group chat."""
        mock_context.bot.get_chat_member.return_value = MagicMock(
            status=ChatMemberStatus.ADMINISTRATOR
        )

        with (
            patch("src.telegram.handlers.get_chat_language", AsyncMock(return_value="ru")),
            patch("src.telegram.handlers.get_gpt_command", AsyncMock(return_value="евлампий")),
        ):
            await start(mock_group_update, mock_context)

            mock_group_update.message.reply_text.assert_called_once()

    async def test_group_chat_owner_allowed(self, mock_group_update, mock_context):
        """Owner sends /start in group chat."""
        mock_context.bot.get_chat_member.return_value = MagicMock(status=ChatMemberStatus.OWNER)

        with (
            patch("src.telegram.handlers.get_chat_language", AsyncMock(return_value="ru")),
            patch("src.telegram.handlers.get_gpt_command", AsyncMock(return_value="евлампий")),
        ):
            await start(mock_group_update, mock_context)

            mock_group_update.message.reply_text.assert_called_once()

    async def test_group_chat_member_blocked(self, mock_group_update, mock_context):
        """Regular member sends /start in group chat - ignored."""
        mock_context.bot.get_chat_member.return_value = MagicMock(status=ChatMemberStatus.MEMBER)

        await start(mock_group_update, mock_context)

        mock_group_update.message.reply_text.assert_not_called()


class TestChooseLanguage:
    """Test /choose_your_language command."""

    async def test_shows_language_buttons(self, mock_private_update, mock_context):
        """User requests language selection - shows inline keyboard."""
        await choose_language(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_args = mock_private_update.message.reply_text.call_args
        assert "reply_markup" in call_args.kwargs

        keyboard = call_args.kwargs["reply_markup"].inline_keyboard
        assert len(keyboard) == 4

    async def test_group_chat_non_admin_blocked(self, mock_group_update, mock_context):
        """Non-admin in group chat - ignored."""
        mock_context.bot.get_chat_member.return_value = MagicMock(status=ChatMemberStatus.MEMBER)

        await choose_language(mock_group_update, mock_context)

        mock_group_update.message.reply_text.assert_not_called()


class TestLanguageButtons:
    """Test language selection button callbacks."""

    @pytest.mark.parametrize(
        "lang_code,expected_text",
        [
            (RUSSIAN, "Русский"),
            (ENGLISH, "English"),
            (SPANISH, "Español"),
            (GERMANY, "Deutsch"),
        ],
    )
    async def test_language_button_sets_language(
        self,
        mock_private_update,
        mock_context,
        mock_callback_query,
        lang_code,
        expected_text,
    ):
        """User clicks language button - language is saved."""
        mock_callback_query.data = f"set_lang_{lang_code}"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        with patch("src.telegram.handlers.set_chat_language", AsyncMock()) as mock_set_lang:
            await lang_buttons(mock_private_update, mock_context)

            mock_set_lang.assert_called_once_with("u_12345", lang_code)
            mock_callback_query.answer.assert_called_once()
            mock_callback_query.edit_message_text.assert_called_once()

    async def test_group_chat_language_button(
        self, mock_group_update, mock_context, mock_callback_query
    ):
        """Admin clicks language button in group chat."""
        mock_callback_query.data = "set_lang_en"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = -100123456
        mock_group_update.callback_query = mock_callback_query
        mock_context.bot.get_chat_member.return_value = MagicMock(
            status=ChatMemberStatus.ADMINISTRATOR
        )

        with patch("src.telegram.handlers.set_chat_language", AsyncMock()) as mock_set_lang:
            await lang_buttons(mock_group_update, mock_context)

            mock_set_lang.assert_called_once_with("g_-100123456", "en")


class TestVoiceMessage:
    """Test voice message processing."""

    async def test_voice_message_translated(self, mock_private_update, mock_context):
        """Voice message is translated to text."""
        from src.telegram.voice import from_voice_to_text

        mock_voice = MagicMock()
        mock_voice.get_file = AsyncMock()
        mock_voice.get_file.return_value.download_as_bytearray = AsyncMock(
            return_value=b"fake_audio_data"
        )
        mock_private_update.message.voice = mock_voice

        with (
            patch("src.telegram.voice.get_chat_language", AsyncMock(return_value="en")),
            patch("src.telegram.voice.get_gpt_command", AsyncMock(return_value="евлампий")),
            patch("src.telegram.voice.transcribe_audio", AsyncMock(return_value=("Hello world", 5))),
            patch("src.telegram.voice.send_response", AsyncMock()) as mock_send,
            patch("src.telegram.voice.save_transcription_to_obsidian", AsyncMock()),
            patch("src.telegram.voice.grant_initial_credits_if_eligible", AsyncMock()),
            patch("src.telegram.voice.has_unlimited_access", return_value=True),
            patch("src.telegram.voice.get_user_tier", AsyncMock(return_value="vip")),
            patch("src.telegram.voice.is_wit_available", AsyncMock(return_value=True)),
            patch("src.telegram.voice.increment_wit_usage", AsyncMock()),
            patch("src.telegram.voice.increment_transcription_stats", AsyncMock()),
            patch("src.telegram.voice.increment_user_stats", AsyncMock()),
            patch("src.telegram.voice.record_groq_usage", AsyncMock()),
        ):
            await from_voice_to_text(mock_private_update, mock_context)

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["response"] == "Hello world"

    async def test_voice_message_with_command_prefix(self, mock_private_update, mock_context):
        """Voice message starting with command triggers GPT response."""
        from src.telegram.voice import from_voice_to_text

        mock_voice = MagicMock()
        mock_voice.get_file = AsyncMock()
        mock_voice.get_file.return_value.download_as_bytearray = AsyncMock(
            return_value=b"fake_audio_data"
        )
        mock_private_update.message.voice = mock_voice

        with (
            patch("src.telegram.voice.get_chat_language", AsyncMock(return_value="ru")),
            patch("src.telegram.voice.get_gpt_command", AsyncMock(return_value="евлампий")),
            patch("src.telegram.voice.transcribe_audio", AsyncMock(return_value=("евлампий расскажи анекдот", 10))),
            patch("src.telegram.voice.send_response", AsyncMock()) as mock_send,
            patch("src.telegram.voice.save_transcription_to_obsidian", AsyncMock()),
            patch("src.telegram.voice.grant_initial_credits_if_eligible", AsyncMock()),
            patch("src.telegram.voice.has_unlimited_access", return_value=True),
            patch("src.telegram.voice.get_user_tier", AsyncMock(return_value="vip")),
            patch("src.telegram.voice.is_wit_available", AsyncMock(return_value=True)),
            patch("src.telegram.voice.increment_wit_usage", AsyncMock()),
            patch("src.telegram.voice.increment_transcription_stats", AsyncMock()),
            patch("src.telegram.voice.increment_user_stats", AsyncMock()),
            patch("src.telegram.voice.record_groq_usage", AsyncMock()),
        ):
            await from_voice_to_text(mock_private_update, mock_context)

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert "Command" in call_kwargs["response"]

    async def test_empty_voice_message_ignored(self, mock_private_update, mock_context):
        """Empty voice transcription produces no response."""
        from src.telegram.voice import from_voice_to_text

        mock_voice = MagicMock()
        mock_voice.get_file = AsyncMock()
        mock_voice.get_file.return_value.download_as_bytearray = AsyncMock(
            return_value=b"fake_audio_data"
        )
        mock_private_update.message.voice = mock_voice

        with (
            patch("src.telegram.voice.get_chat_language", AsyncMock(return_value="en")),
            patch("src.telegram.voice.get_gpt_command", AsyncMock(return_value="евлампий")),
            patch("src.telegram.voice.transcribe_audio", AsyncMock(return_value=("", 0))),
            patch("src.telegram.voice.send_response", AsyncMock()) as mock_send,
            patch("src.telegram.voice.save_transcription_to_obsidian", AsyncMock()),
            patch("src.telegram.voice.grant_initial_credits_if_eligible", AsyncMock()),
            patch("src.telegram.voice.has_unlimited_access", return_value=True),
            patch("src.telegram.voice.get_user_tier", AsyncMock(return_value="vip")),
            patch("src.telegram.voice.is_wit_available", AsyncMock(return_value=True)),
            patch("src.telegram.voice.increment_wit_usage", AsyncMock()),
            patch("src.telegram.voice.increment_transcription_stats", AsyncMock()),
            patch("src.telegram.voice.increment_user_stats", AsyncMock()),
            patch("src.telegram.voice.record_groq_usage", AsyncMock()),
        ):
            await from_voice_to_text(mock_private_update, mock_context)

            mock_send.assert_not_called()


class TestBotRemoval:
    """Test scenarios when user removes/blocks the bot.

    TODO: ChatMemberUpdated handler is not implemented in current codebase.
    """

    @pytest.mark.skip(reason="ChatMemberUpdated handler not implemented")
    async def test_user_blocks_bot_in_private_chat(self):
        """User blocks bot - cleanup user data."""
        pass

    @pytest.mark.skip(reason="ChatMemberUpdated handler not implemented")
    async def test_bot_removed_from_group(self):
        """Bot removed from group - cleanup group data."""
        pass


class TestEnterYourCommand:
    """Test /enter_your_command handler."""

    async def test_prompts_for_command_input(self, mock_private_update, mock_context):
        """User is prompted to enter custom command."""
        from src.telegram.handlers import WAITING_FOR_COMMAND, enter_your_command

        result = await enter_your_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once_with(
            "Please enter your command for GPT:"
        )
        assert result == WAITING_FOR_COMMAND

    async def test_non_admin_blocked_in_group(self, mock_group_update, mock_context):
        """Non-admin in group chat - returns END."""
        from telegram.ext import ConversationHandler

        from src.telegram.handlers import enter_your_command

        mock_context.bot.get_chat_member.return_value = MagicMock(status=ChatMemberStatus.MEMBER)

        result = await enter_your_command(mock_group_update, mock_context)

        mock_group_update.message.reply_text.assert_not_called()
        assert result == ConversationHandler.END


class TestHandleCommandInput:
    """Test command input handler."""

    async def test_saves_custom_command(self, mock_private_update, mock_context):
        """Custom command is saved."""
        from telegram.ext import ConversationHandler

        from src.telegram.handlers import handle_command_input

        mock_private_update.message.text = "my_custom_command"

        with patch("src.telegram.handlers.set_gpt_command", AsyncMock()) as mock_set_cmd:
            result = await handle_command_input(mock_private_update, mock_context)

            mock_set_cmd.assert_called_once_with("u_12345", "my_custom_command")
            mock_private_update.message.reply_text.assert_called_once()
            assert "my_custom_command" in mock_private_update.message.reply_text.call_args[0][0]
            assert result == ConversationHandler.END


class TestConnectGithub:
    """Test /connect_github command."""

    async def test_sends_device_code_message(self, mock_private_update, mock_context):
        """User receives device code and verification URL."""
        from src.telegram.handlers import connect_github

        device_info = {
            "device_code": "abc123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }

        with (
            patch(
                "src.telegram.handlers.get_github_device_code",
                AsyncMock(return_value=device_info),
            ),
            patch("src.telegram.handlers.asyncio.create_task"),
        ):
            await connect_github(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "ABCD-1234" in reply_text
        assert "github.com/login/device" in reply_text

    async def test_handles_device_code_error(self, mock_private_update, mock_context):
        """Error response from device code request."""
        from src.telegram.handlers import connect_github

        with patch(
            "src.telegram.handlers.get_github_device_code",
            AsyncMock(return_value={"error": "unauthorized_client"}),
        ):
            await connect_github(mock_private_update, mock_context)

        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "Failed" in reply_text


class TestToggleObsidian:
    """Test /toggle_obsidian command."""

    async def test_toggles_on(self, mock_private_update, mock_context):
        """Enables Obsidian sync when currently disabled."""
        from src.telegram.handlers import toggle_obsidian

        with (
            patch("src.telegram.handlers.get_save_to_obsidian", AsyncMock(return_value=False)),
            patch("src.telegram.handlers.set_save_to_obsidian", AsyncMock()) as mock_set,
        ):
            await toggle_obsidian(mock_private_update, mock_context)

        mock_set.assert_called_once_with("u_12345", True)
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "enabled" in reply_text

    async def test_toggles_off(self, mock_private_update, mock_context):
        """Disables Obsidian sync when currently enabled."""
        from src.telegram.handlers import toggle_obsidian

        with (
            patch("src.telegram.handlers.get_save_to_obsidian", AsyncMock(return_value=True)),
            patch("src.telegram.handlers.set_save_to_obsidian", AsyncMock()) as mock_set,
        ):
            await toggle_obsidian(mock_private_update, mock_context)

        mock_set.assert_called_once_with("u_12345", False)
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "disabled" in reply_text


class TestDisconnectGithub:
    """Test /disconnect_github command."""

    async def test_clears_settings(self, mock_private_update, mock_context):
        """GitHub settings are cleared."""
        from src.telegram.handlers import disconnect_github

        with patch("src.telegram.handlers.clear_github_settings", AsyncMock()) as mock_clear:
            await disconnect_github(mock_private_update, mock_context)

        mock_clear.assert_called_once_with("u_12345")
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "disconnected" in reply_text.lower()
