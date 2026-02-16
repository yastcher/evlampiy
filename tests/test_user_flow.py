from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.constants import ChatMemberStatus
from telegram.ext import ConversationHandler

from src.account_linking import confirm_link, generate_link_code
from src.config import ENGLISH, GERMAN, RUSSIAN, SPANISH
from src.credits import add_credits, current_month_key, deduct_credits
from src.dto import MonthlyStats
from src.mongo import (
    add_user_role,
    get_auto_categorize,
    get_auto_cleanup,
    get_chat_language,
    get_github_settings,
    get_gpt_command,
    get_save_to_obsidian,
    set_auto_categorize,
    set_auto_cleanup,
    set_chat_language,
    set_github_settings,
    set_gpt_command,
    set_save_to_obsidian,
)
from src.telegram.handlers import (
    WAITING_FOR_COMMAND,
    account_hub,
    categorize_all,
    choose_language,
    connect_github,
    disconnect_github,
    enter_your_command,
    handle_command_input,
    hub_callback_router,
    lang_buttons,
    obsidian_hub,
    settings_hub,
    start,
    toggle_categorize,
    toggle_cleanup,
    toggle_obsidian,
)
from src.telegram.voice import from_voice_to_text


class TestStartCommand:
    """Test /start command in different contexts."""

    async def test_private_chat_new_user(self, mock_private_update, mock_context):
        """New user sends /start in private chat."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_gpt_command(chat_id, "евлампий")

        await start(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "voice" in reply_text.lower()
        assert "en" in reply_text

    async def test_group_chat_admin_allowed(self, mock_group_update, mock_context):
        """Admin sends /start in group chat."""
        chat_id = "g_-100123456"
        await set_chat_language(chat_id, "ru")
        await set_gpt_command(chat_id, "евлампий")

        mock_context.bot.get_chat_member.return_value = MagicMock(
            status=ChatMemberStatus.ADMINISTRATOR
        )

        await start(mock_group_update, mock_context)

        mock_group_update.message.reply_text.assert_called_once()

    async def test_group_chat_owner_allowed(self, mock_group_update, mock_context):
        """Owner sends /start in group chat."""
        chat_id = "g_-100123456"
        await set_chat_language(chat_id, "ru")
        await set_gpt_command(chat_id, "евлампий")

        mock_context.bot.get_chat_member.return_value = MagicMock(status=ChatMemberStatus.OWNER)

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
            (GERMAN, "Deutsch"),
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
        """User clicks language button - language is saved to DB."""
        chat_id = "u_12345"
        mock_callback_query.data = f"set_lang_{lang_code}"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        await lang_buttons(mock_private_update, mock_context)

        # Verify language was saved to real DB
        saved_language = await get_chat_language(chat_id)
        assert saved_language == lang_code
        mock_callback_query.answer.assert_called_once()
        mock_callback_query.edit_message_text.assert_called_once()

    async def test_group_chat_language_button(
        self, mock_group_update, mock_context, mock_callback_query
    ):
        """Admin clicks language button in group chat."""
        chat_id = "g_-100123456"
        mock_callback_query.data = "set_lang_en"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = -100123456
        mock_group_update.callback_query = mock_callback_query
        mock_context.bot.get_chat_member.return_value = MagicMock(
            status=ChatMemberStatus.ADMINISTRATOR
        )

        await lang_buttons(mock_group_update, mock_context)

        # Verify language was saved to real DB
        saved_language = await get_chat_language(chat_id)
        assert saved_language == "en"


class TestVoiceMessageFlow:
    """Test voice message processing flow with real DB operations."""

    async def test_no_voice_or_audio_returns_early(self, mock_private_update, mock_context):
        """Handler returns early when no voice/audio message attached."""
        mock_private_update.message.voice = None
        mock_private_update.message.audio = None

        await from_voice_to_text(mock_private_update, mock_context)

        # No errors, no responses
        mock_private_update.message.reply_text.assert_not_called()

    async def test_no_effective_user_returns_early(
        self, mock_private_update, mock_context, mock_telegram_voice
    ):
        """Handler returns early when effective_user is None (channel forward)."""
        mock_private_update.message.voice = mock_telegram_voice
        mock_private_update.effective_user = None

        await from_voice_to_text(mock_private_update, mock_context)
        mock_private_update.message.reply_text.assert_not_called()

    async def test_blocked_user_rejected(
        self, mock_private_update, mock_context, mock_telegram_voice
    ):
        """Blocked user gets rejected with blocked message."""
        user_id = "12360"
        chat_id = "u_12360"
        mock_private_update.effective_user.id = 12360
        mock_private_update.effective_chat.id = 12360

        await set_chat_language(chat_id, "en")
        await add_user_role(user_id, "blocked", "admin")
        mock_private_update.message.voice = mock_telegram_voice

        with patch("src.telegram.voice.send_response", AsyncMock()) as mock_send:
            await from_voice_to_text(mock_private_update, mock_context)

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert "blocked" in call_kwargs["response"].lower()

    async def test_audio_message_processed(
        self, mock_private_update, mock_context, mock_telegram_audio, voice_external_mocks
    ):
        """Audio messages (not just voice) are processed."""
        user_id = "12361"
        chat_id = "u_12361"
        mock_private_update.effective_user.id = 12361
        mock_private_update.effective_chat.id = 12361

        await set_chat_language(chat_id, "en")
        await add_credits(user_id, 100)
        mock_private_update.message.voice = None
        mock_private_update.message.audio = mock_telegram_audio
        voice_external_mocks["transcribe"].return_value = ("Audio text", 30)

        await from_voice_to_text(mock_private_update, mock_context)

        call_kwargs = voice_external_mocks["send"].call_args.kwargs
        assert call_kwargs["response"] == "Audio text"

    async def test_service_unavailable_when_no_provider(
        self, mock_private_update, mock_context, mock_telegram_voice, voice_external_mocks
    ):
        """Shows service unavailable when no transcription provider available."""
        chat_id = "u_12350"
        mock_private_update.effective_user.id = 12350
        mock_private_update.effective_chat.id = 12350

        await set_chat_language(chat_id, "en")
        mock_private_update.message.voice = mock_telegram_voice

        with (
            patch("src.telegram.voice.is_wit_available", AsyncMock(return_value=False)),
            patch("src.telegram.voice.settings.groq_api_key", ""),
        ):
            await from_voice_to_text(mock_private_update, mock_context)

        call_kwargs = voice_external_mocks["send"].call_args.kwargs
        assert "unavailable" in call_kwargs["response"].lower()

    async def test_insufficient_credits_message(
        self, mock_private_update, mock_context, mock_telegram_voice, voice_external_mocks
    ):
        """Shows insufficient tokens when user has no tokens."""
        user_id = "12351"
        chat_id = "u_12351"
        mock_private_update.effective_user.id = 12351
        mock_private_update.effective_chat.id = 12351

        await set_chat_language(chat_id, "en")
        await deduct_credits(user_id, 100)
        mock_private_update.message.voice = mock_telegram_voice

        with patch("src.telegram.voice.is_wit_available", AsyncMock(return_value=True)):
            await from_voice_to_text(mock_private_update, mock_context)

        call_kwargs = voice_external_mocks["send"].call_args.kwargs
        assert "token" in call_kwargs["response"].lower()

    async def test_groq_provider_records_usage(
        self, mock_private_update, mock_context, mock_telegram_voice, voice_external_mocks
    ):
        """Groq provider usage is recorded in stats."""
        user_id = "12352"
        chat_id = "u_12352"
        mock_private_update.effective_user.id = 12352
        mock_private_update.effective_chat.id = 12352

        await set_chat_language(chat_id, "en")
        await add_credits(user_id, 100)
        mock_private_update.message.voice = mock_telegram_voice
        voice_external_mocks["transcribe"].return_value = ("Hello", 10)

        with (
            patch("src.telegram.voice.is_wit_available", AsyncMock(return_value=False)),
            patch("src.telegram.voice.settings.groq_api_key", "test-key"),
        ):
            await from_voice_to_text(mock_private_update, mock_context)

        month_key = current_month_key()
        stats = await MonthlyStats.find_one(MonthlyStats.month_key == month_key)
        assert stats is not None
        assert stats.groq_audio_seconds >= 10

    async def test_voice_message_with_auto_categorize(
        self, mock_private_update, mock_context, mock_telegram_voice, voice_external_mocks
    ):
        """Voice message triggers auto-categorization when enabled."""
        user_id = "12353"
        chat_id = "u_12353"
        mock_private_update.effective_user.id = 12353
        mock_private_update.effective_chat.id = 12353

        await set_chat_language(chat_id, "en")
        await set_gpt_command(chat_id, "евлампий")
        await add_credits(user_id, 100)
        await set_github_settings(chat_id, "owner", "repo", "token")
        await set_auto_categorize(chat_id, True)

        mock_private_update.message.voice = mock_telegram_voice
        voice_external_mocks["transcribe"].return_value = ("Note content", 5)
        voice_external_mocks["obsidian"].return_value = (True, "note.md")

        await from_voice_to_text(mock_private_update, mock_context)

        voice_external_mocks["categorize"].assert_called_once()

    async def test_voice_message_flow(
        self, mock_private_update, mock_context, mock_telegram_voice, voice_external_mocks
    ):
        """Complete voice message flow: setup user -> transcribe -> response."""
        user_id = "12345"
        chat_id = "u_12345"

        await set_chat_language(chat_id, "en")
        await set_gpt_command(chat_id, "евлампий")
        await add_credits(user_id, 100)

        mock_private_update.message.voice = mock_telegram_voice

        await from_voice_to_text(mock_private_update, mock_context)

        call_kwargs = voice_external_mocks["send"].call_args.kwargs
        assert call_kwargs["response"] == "Hello world"

    async def test_voice_message_with_command_prefix(
        self, mock_private_update, mock_context, mock_telegram_voice, voice_external_mocks
    ):
        """Voice message starting with command triggers GPT response indicator."""
        user_id = "12346"
        chat_id = "u_12346"
        mock_private_update.effective_user.id = 12346
        mock_private_update.effective_chat.id = 12346

        await set_chat_language(chat_id, "ru")
        await set_gpt_command(chat_id, "евлампий")
        await add_credits(user_id, 100)

        mock_private_update.message.voice = mock_telegram_voice
        voice_external_mocks["transcribe"].return_value = ("евлампий расскажи анекдот", 10)

        await from_voice_to_text(mock_private_update, mock_context)

        call_kwargs = voice_external_mocks["send"].call_args.kwargs
        assert "Command" in call_kwargs["response"]

    async def test_empty_voice_message_ignored(
        self, mock_private_update, mock_context, mock_telegram_voice, voice_external_mocks
    ):
        """Empty voice transcription produces no response."""
        user_id = "12347"
        chat_id = "u_12347"
        mock_private_update.effective_user.id = 12347
        mock_private_update.effective_chat.id = 12347

        await set_chat_language(chat_id, "en")
        await add_credits(user_id, 100)

        mock_private_update.message.voice = mock_telegram_voice
        voice_external_mocks["transcribe"].return_value = ("", 0)

        await from_voice_to_text(mock_private_update, mock_context)

        voice_external_mocks["send"].assert_not_called()


class TestVoiceMessageWithCleanup:
    """Test voice message flow with transcript cleanup."""

    async def test_voice_message_with_cleanup_enabled(
        self, mock_private_update, mock_context, mock_telegram_voice, voice_external_mocks
    ):
        """Voice message triggers cleanup when enabled for paid user."""
        user_id = "12360"
        chat_id = "u_12360"
        mock_private_update.effective_user.id = 12360
        mock_private_update.effective_chat.id = 12360

        await set_chat_language(chat_id, "en")
        await set_gpt_command(chat_id, "евлампий")
        await add_credits(user_id, 100)
        await set_auto_cleanup(chat_id, True)

        mock_private_update.message.voice = mock_telegram_voice
        voice_external_mocks["transcribe"].return_value = (
            "ну вот значит я хотел сказать что проект классный",
            5,
        )
        voice_external_mocks["cleanup"].side_effect = None
        voice_external_mocks["cleanup"].return_value = "Я хотел сказать, что проект классный."

        await from_voice_to_text(mock_private_update, mock_context)

        voice_external_mocks["cleanup"].assert_called_once()


class TestToggleCleanup:
    """Test /toggle_cleanup command with real DB."""

    async def test_enables_cleanup(self, mock_private_update, mock_context):
        """Enables text cleanup when currently disabled."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_auto_cleanup(chat_id, False)

        await toggle_cleanup(mock_private_update, mock_context)

        assert await get_auto_cleanup(chat_id) is True
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "enabled" in reply_text.lower()

    async def test_disables_cleanup(self, mock_private_update, mock_context):
        """Disables text cleanup when currently enabled."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_auto_cleanup(chat_id, True)

        await toggle_cleanup(mock_private_update, mock_context)

        assert await get_auto_cleanup(chat_id) is False
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "disabled" in reply_text.lower()


class TestEnterYourCommand:
    """Test /enter_your_command handler."""

    async def test_prompts_for_command_input(self, mock_private_update, mock_context):
        """User is prompted to enter custom command."""
        result = await enter_your_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once_with(
            "Please enter your command for GPT:"
        )
        assert result == WAITING_FOR_COMMAND

    async def test_non_admin_blocked_in_group(self, mock_group_update, mock_context):
        """Non-admin in group chat - returns END."""
        mock_context.bot.get_chat_member.return_value = MagicMock(status=ChatMemberStatus.MEMBER)

        result = await enter_your_command(mock_group_update, mock_context)

        mock_group_update.message.reply_text.assert_not_called()
        assert result == ConversationHandler.END


class TestHandleCommandInput:
    """Test command input handler with real DB."""

    async def test_saves_custom_command(self, mock_private_update, mock_context):
        """Custom command is saved to real DB."""
        chat_id = "u_12345"
        mock_private_update.message.text = "my_custom_command"

        result = await handle_command_input(mock_private_update, mock_context)

        # Verify command was saved to real DB
        saved_command = await get_gpt_command(chat_id)
        assert saved_command == "my_custom_command"
        mock_private_update.message.reply_text.assert_called_once()
        assert "my_custom_command" in mock_private_update.message.reply_text.call_args[0][0]
        assert result == ConversationHandler.END


class TestConnectGithub:
    """Test /connect_github command."""

    async def test_sends_device_code_message(self, mock_private_update, mock_context):
        """User receives device code and verification URL."""
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
        await set_chat_language("u_12345", "en")

        with patch(
            "src.telegram.handlers.get_github_device_code",
            AsyncMock(return_value={"error": "unauthorized_client"}),
        ):
            await connect_github(mock_private_update, mock_context)

        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "Failed" in reply_text


class TestToggleObsidian:
    """Test /toggle_obsidian command with real DB."""

    async def test_toggles_on(self, mock_private_update, mock_context):
        """Enables Obsidian sync when currently disabled."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        # Ensure initially disabled
        await set_save_to_obsidian(chat_id, False)

        await toggle_obsidian(mock_private_update, mock_context)

        # Verify state changed in real DB
        assert await get_save_to_obsidian(chat_id) is True
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "enabled" in reply_text

    async def test_toggles_off(self, mock_private_update, mock_context):
        """Disables Obsidian sync when currently enabled."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        # Ensure initially enabled
        await set_save_to_obsidian(chat_id, True)

        await toggle_obsidian(mock_private_update, mock_context)

        # Verify state changed in real DB
        assert await get_save_to_obsidian(chat_id) is False
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "disabled" in reply_text


class TestDisconnectGithub:
    """Test /disconnect_github command with real DB."""

    async def test_clears_settings(self, mock_private_update, mock_context):
        """GitHub settings are cleared in real DB."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        # Setup GitHub settings first
        await set_github_settings(chat_id, "testowner", "testrepo", "ghp_test")
        await set_save_to_obsidian(chat_id, True)

        await disconnect_github(mock_private_update, mock_context)

        # Verify settings cleared in real DB
        assert await get_github_settings(chat_id) == {}
        assert await get_save_to_obsidian(chat_id) is False
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "disconnected" in reply_text.lower()


class TestToggleCategorize:
    """Test /toggle_categorize command with real DB."""

    async def test_enables_categorization(self, mock_private_update, mock_context):
        """Enables auto-categorization when currently disabled."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_auto_categorize(chat_id, False)

        await toggle_categorize(mock_private_update, mock_context)

        # Verify state changed in real DB
        assert await get_auto_categorize(chat_id) is True
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "enabled" in reply_text.lower()

    async def test_disables_categorization(self, mock_private_update, mock_context):
        """Disables auto-categorization when currently enabled."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_auto_categorize(chat_id, True)

        await toggle_categorize(mock_private_update, mock_context)

        # Verify state changed in real DB
        assert await get_auto_categorize(chat_id) is False
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "disabled" in reply_text.lower()


class TestCategorizeAll:
    """Test /categorize command with real DB for settings."""

    async def test_categorizes_files(self, mock_private_update, mock_context):
        """Categorizes all files in income folder."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_github_settings(chat_id, "testowner", "testrepo", "ghp_test")

        with patch("src.telegram.handlers.categorize_all_income", AsyncMock(return_value=5)):
            await categorize_all(mock_private_update, mock_context)

        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "5" in reply_text

    async def test_shows_no_files_message(self, mock_private_update, mock_context):
        """Shows message when no files to categorize."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_github_settings(chat_id, "testowner", "testrepo", "ghp_test")

        with patch("src.telegram.handlers.categorize_all_income", AsyncMock(return_value=0)):
            await categorize_all(mock_private_update, mock_context)

        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "no files" in reply_text.lower()

    async def test_requires_github_connection(self, mock_private_update, mock_context):
        """Shows error when GitHub not connected."""
        chat_id = "u_categorize_no_gh"
        mock_private_update.effective_chat.id = 999999
        mock_private_update.effective_user.id = 999999
        await set_chat_language(chat_id, "en")
        # No GitHub settings configured

        await categorize_all(mock_private_update, mock_context)

        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "GitHub" in reply_text


class TestHubCommands:
    """Test hub commands (/settings, /obsidian, /account)."""

    async def test_settings_hub_shows_keyboard(self, mock_private_update, mock_context):
        """Settings hub shows inline keyboard with 2 buttons."""

        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")

        await settings_hub(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_args = mock_private_update.message.reply_text.call_args
        assert "reply_markup" in call_args.kwargs

        keyboard = call_args.kwargs["reply_markup"].inline_keyboard
        # Should have 2 buttons: Language and GPT command
        assert len(keyboard) == 2
        assert "hub_language" in keyboard[0][0].callback_data
        assert "hub_gpt_command" in keyboard[1][0].callback_data

    async def test_settings_hub_blocked_for_non_admin_in_group(
        self, mock_group_update, mock_context
    ):
        """Non-admin in group chat cannot use settings hub."""

        mock_context.bot.get_chat_member.return_value = MagicMock(status=ChatMemberStatus.MEMBER)

        await settings_hub(mock_group_update, mock_context)

        mock_group_update.message.reply_text.assert_not_called()

    async def test_obsidian_hub_without_github(self, mock_private_update, mock_context):
        """Obsidian hub shows only 'Connect GitHub' when not connected."""

        chat_id = "u_obsidian_no_gh"
        mock_private_update.effective_chat.id = 888888
        mock_private_update.effective_user.id = 888888
        await set_chat_language(chat_id, "en")
        # No GitHub settings

        await obsidian_hub(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_args = mock_private_update.message.reply_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard

        # Only one button: Connect GitHub
        assert len(keyboard) == 1
        assert "hub_connect_github" in keyboard[0][0].callback_data

    async def test_obsidian_hub_with_github(self, mock_private_update, mock_context):
        """Obsidian hub shows all buttons except 'Connect' when GitHub connected."""

        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_github_settings(chat_id, "owner", "repo", "token")
        await set_save_to_obsidian(chat_id, True)
        await set_auto_categorize(chat_id, False)

        await obsidian_hub(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_args = mock_private_update.message.reply_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard

        # Should have: toggle_sync, toggle_sort, categorize, disconnect
        callback_datas = [row[0].callback_data for row in keyboard]
        assert "hub_toggle_obsidian" in callback_datas
        assert "hub_toggle_categorize" in callback_datas
        assert "hub_categorize" in callback_datas
        assert "hub_disconnect_github" in callback_datas
        assert "hub_connect_github" not in callback_datas

    async def test_account_hub_shows_balance_buttons(self, mock_private_update, mock_context):
        """Account hub shows buy, balance, mystats buttons."""

        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")

        await account_hub(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_args = mock_private_update.message.reply_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard

        callback_datas = [row[0].callback_data for row in keyboard]
        assert "hub_buy" in callback_datas
        assert "hub_balance" in callback_datas
        assert "hub_mystats" in callback_datas

    async def test_account_hub_shows_link_whatsapp(self, mock_private_update, mock_context):
        """Account hub shows 'Link WhatsApp' when not linked."""

        chat_id = "u_account_no_wa"
        mock_private_update.effective_chat.id = 777777
        mock_private_update.effective_user.id = 777777
        await set_chat_language(chat_id, "en")
        # No WhatsApp linked

        await account_hub(mock_private_update, mock_context)

        call_args = mock_private_update.message.reply_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard

        callback_datas = [row[0].callback_data for row in keyboard]
        assert "hub_link_whatsapp" in callback_datas
        assert "hub_unlink_whatsapp" not in callback_datas

    async def test_account_hub_shows_unlink_whatsapp(self, mock_private_update, mock_context):
        """Account hub shows 'Unlink WhatsApp' when linked."""

        user_id = "12345"
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")

        # Link WhatsApp
        code = await generate_link_code(user_id)
        await confirm_link(code, "+1234567890")

        await account_hub(mock_private_update, mock_context)

        call_args = mock_private_update.message.reply_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard

        callback_datas = [row[0].callback_data for row in keyboard]
        assert "hub_unlink_whatsapp" in callback_datas
        assert "hub_link_whatsapp" not in callback_datas

    async def test_account_hub_private_only(self, mock_group_update, mock_context):
        """Account hub only works in private chats."""

        await account_hub(mock_group_update, mock_context)

        mock_group_update.message.reply_text.assert_not_called()

    async def test_hub_callback_triggers_language(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Clicking language button in hub opens language selection."""
        mock_callback_query.data = "hub_language"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        await hub_callback_router(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.edit_message_text.assert_called_once()
        # Should show language keyboard
        call_args = mock_callback_query.edit_message_text.call_args
        assert "reply_markup" in call_args.kwargs


class TestHubCallbackRouting:
    """Test hub inline button callbacks route to actual handlers."""

    async def test_account_balance_callback(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Clicking Balance button in account hub shows balance."""
        user_id = "12345"
        await add_credits(user_id, 75)

        mock_callback_query.data = "hub_balance"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query
        mock_context.bot.send_message = AsyncMock()

        await hub_callback_router(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        message_text = mock_context.bot.send_message.call_args[1]["text"]
        assert "75" in message_text

    async def test_account_buy_callback(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Clicking Buy button in account hub shows package keyboard."""
        mock_callback_query.data = "hub_buy"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_callback_query.message.reply_text = AsyncMock()
        mock_private_update.callback_query = mock_callback_query
        mock_private_update.message = None

        await hub_callback_router(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.message.reply_text.assert_called_once()

    async def test_account_mystats_callback(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Clicking MyStats button in account hub shows stats."""
        mock_callback_query.data = "hub_mystats"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_callback_query.message.reply_text = AsyncMock()
        mock_private_update.callback_query = mock_callback_query

        await hub_callback_router(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.message.reply_text.assert_called_once()

    async def test_obsidian_toggle_callback(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Clicking toggle sync in obsidian hub toggles obsidian sync."""
        chat_id = "u_12345"
        await set_save_to_obsidian(chat_id, False)

        mock_callback_query.data = "hub_toggle_obsidian"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_callback_query.message.reply_text = AsyncMock()
        mock_private_update.callback_query = mock_callback_query

        await hub_callback_router(mock_private_update, mock_context)

        assert await get_save_to_obsidian(chat_id) is True

    async def test_unlink_whatsapp_callback(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Clicking unlink WhatsApp in account hub unlinks account."""
        mock_callback_query.data = "hub_unlink_whatsapp"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_callback_query.message.reply_text = AsyncMock()
        mock_private_update.callback_query = mock_callback_query

        await hub_callback_router(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.message.reply_text.assert_called_once()
