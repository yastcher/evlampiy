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
            assert "translate" in reply_text.lower()
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
            patch("src.telegram.voice.transcribe_audio", return_value="Hello world"),
            patch("src.telegram.voice.send_response", AsyncMock()) as mock_send,
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
            patch("src.telegram.voice.transcribe_audio", return_value="евлампий расскажи анекдот"),
            patch("src.telegram.voice.send_response", AsyncMock()) as mock_send,
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
            patch("src.telegram.voice.transcribe_audio", return_value=""),
            patch("src.telegram.voice.send_response", AsyncMock()) as mock_send,
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


class TestSetGithubCommand:
    """Test /set_github command."""

    async def test_saves_github_settings(self, mock_private_update, mock_context):
        """GitHub settings are saved with valid input."""
        from src.telegram.handlers import set_github_command

        mock_private_update.message.text = "/set_github owner repo ghp_token123"

        with patch("src.telegram.handlers.set_github_settings", AsyncMock()) as mock_set_gh:
            await set_github_command(mock_private_update, mock_context)

            mock_set_gh.assert_called_once_with("u_12345", "owner", "repo", "ghp_token123")
            mock_private_update.message.reply_text.assert_called_once_with("GitHub settings saved.")

    async def test_shows_usage_for_invalid_input(self, mock_private_update, mock_context):
        """Usage message is shown for invalid input."""
        from src.telegram.handlers import set_github_command

        mock_private_update.message.text = "/set_github owner"

        await set_github_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        assert "Usage:" in mock_private_update.message.reply_text.call_args[0][0]

    async def test_skips_when_no_message(self, mock_private_update, mock_context):
        """Skips when no message."""
        from src.telegram.handlers import set_github_command

        mock_private_update.message = None

        await set_github_command(mock_private_update, mock_context)
        # No error should occur

    async def test_skips_when_no_text(self, mock_private_update, mock_context):
        """Skips when no text."""
        from src.telegram.handlers import set_github_command

        mock_private_update.message.text = None

        await set_github_command(mock_private_update, mock_context)
        # No error should occur


class TestConnectGithub:
    """Test /connect_github command."""

    async def test_calls_authorize_github(self, mock_private_update, mock_context):
        """Authorize function is called."""
        from src.telegram.handlers import connect_github

        with patch("src.telegram.handlers.authorize_github_for_user", AsyncMock()) as mock_auth:
            await connect_github(mock_private_update, mock_context)

            mock_auth.assert_called_once_with(mock_private_update, mock_context)
