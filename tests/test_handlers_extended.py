"""Extended handler tests: coverage for connect_github OAuth flow, toggle_cleanup,
setup_obsidian_git, provider menu, enter_command_from_hub, build_stats_text,
lang_buttons in group chat."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.constants import ChatMemberStatus
from telegram.ext import ConversationHandler

from src import const
from src.credits import add_credits
from src.github_api import GitHubRepo
from src.mongo import (
    get_auto_cleanup,
    get_chat_language,
    get_github_settings,
    get_save_to_obsidian,
    set_auto_cleanup,
    set_chat_language,
    set_github_settings,
    set_preferred_provider,
)
from src.telegram.handlers import (
    WAITING_FOR_COMMAND,
    build_stats_text,
    connect_github,
    enter_your_command_from_hub,
    hub_callback_router,
    lang_buttons,
    setup_obsidian_git,
    toggle_cleanup,
)


class TestToggleCleanup:
    """Test /toggle_cleanup command with real DB."""

    async def test_enables_cleanup(self, mock_private_update, mock_context):
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_auto_cleanup(chat_id, False)

        await toggle_cleanup(mock_private_update, mock_context)

        assert await get_auto_cleanup(chat_id) is True
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "enabled" in reply_text.lower()

    async def test_disables_cleanup(self, mock_private_update, mock_context):
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_auto_cleanup(chat_id, True)

        await toggle_cleanup(mock_private_update, mock_context)

        assert await get_auto_cleanup(chat_id) is False
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "disabled" in reply_text.lower()


class TestConnectGithubOAuthFlow:
    """Test connect_github background task _poll_and_setup with real DB."""

    async def test_successful_oauth_saves_settings(self, mock_private_update, mock_context):
        """Successful OAuth flow: poll returns token, repo created, settings saved."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")

        device_info = {
            "verification_uri": "https://github.com/login/device",
            "user_code": "ABCD-1234",
            "device_code": "dc_test",
            "expires_in": 900,
            "interval": 5,
        }
        repo = GitHubRepo(token="ghp_test", owner="testowner", repo="testrepo")

        with (
            patch(
                "src.telegram.handlers.get_github_device_code",
                AsyncMock(return_value=device_info),
            ),
            patch(
                "src.telegram.handlers.poll_github_for_token",
                AsyncMock(return_value="ghp_test"),
            ),
            patch(
                "src.telegram.handlers.get_or_create_obsidian_repo",
                AsyncMock(return_value=repo),
            ),
        ):
            await connect_github(mock_private_update, mock_context)

            await asyncio.sleep(0.1)  # wait for background task

        # Verify settings persisted in real DB
        saved = await get_github_settings(chat_id)
        assert saved is not None
        assert saved.owner == "testowner"
        assert saved.repo == "testrepo"
        assert await get_save_to_obsidian(chat_id) is True

        # Verify confirmation sent
        mock_context.bot.send_message.assert_called()
        msg = mock_context.bot.send_message.call_args[1]["text"]
        assert "testowner" in msg

    async def test_oauth_timeout_sends_message(self, mock_private_update, mock_context):
        """Poll returns None (timeout) — user gets timeout message."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")

        device_info = {
            "verification_uri": "https://github.com/login/device",
            "user_code": "ABCD-1234",
            "device_code": "dc_test",
            "expires_in": 900,
            "interval": 5,
        }

        with (
            patch(
                "src.telegram.handlers.get_github_device_code",
                AsyncMock(return_value=device_info),
            ),
            patch(
                "src.telegram.handlers.poll_github_for_token",
                AsyncMock(return_value=None),
            ),
        ):
            await connect_github(mock_private_update, mock_context)

            await asyncio.sleep(0.1)  # wait for background task

        # Verify timeout message sent
        mock_context.bot.send_message.assert_called()
        msg = mock_context.bot.send_message.call_args[1]["text"]
        assert "expired" in msg.lower() or "timeout" in msg.lower() or "timed" in msg.lower()

    async def test_oauth_repo_creation_failure(self, mock_private_update, mock_context):
        """Token received but repo creation fails — error message sent."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")

        device_info = {
            "verification_uri": "https://github.com/login/device",
            "user_code": "ABCD-1234",
            "device_code": "dc_test",
            "expires_in": 900,
            "interval": 5,
        }

        with (
            patch(
                "src.telegram.handlers.get_github_device_code",
                AsyncMock(return_value=device_info),
            ),
            patch(
                "src.telegram.handlers.poll_github_for_token",
                AsyncMock(return_value="ghp_test"),
            ),
            patch(
                "src.telegram.handlers.get_or_create_obsidian_repo",
                AsyncMock(return_value=None),
            ),
        ):
            await connect_github(mock_private_update, mock_context)

            await asyncio.sleep(0.1)  # wait for background task

        # Verify error message sent
        mock_context.bot.send_message.assert_called()
        msg = mock_context.bot.send_message.call_args[1]["text"]
        assert "failed" in msg.lower() or "error" in msg.lower()


class TestSetupObsidianGit:
    """Test setup_obsidian_git hub callback with real DB."""

    async def test_success(self, mock_private_update, mock_context, mock_callback_query):
        """Obsidian-git config created successfully."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_github_settings(chat_id, "owner", "repo", "ghp_test")

        mock_callback_query.data = "hub_setup_obsidian_git"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        with patch(
            "src.telegram.handlers.create_obsidian_git_config",
            AsyncMock(return_value=True),
        ):
            await setup_obsidian_git(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        alert_text = mock_callback_query.answer.call_args[0][0]
        assert alert_text  # non-empty response

    async def test_failure(self, mock_private_update, mock_context, mock_callback_query):
        """Obsidian-git config creation fails."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_github_settings(chat_id, "owner", "repo", "ghp_test")

        mock_callback_query.data = "hub_setup_obsidian_git"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        with patch(
            "src.telegram.handlers.create_obsidian_git_config",
            AsyncMock(return_value=False),
        ):
            await setup_obsidian_git(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()

    async def test_no_github_connected(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Shows error when GitHub not connected."""
        chat_id = "u_77777"
        mock_private_update.effective_chat.id = 77777
        mock_private_update.effective_user.id = 77777
        mock_callback_query.from_user.id = 77777
        mock_callback_query.message.chat.id = 77777
        await set_chat_language(chat_id, "en")

        mock_callback_query.data = "hub_setup_obsidian_git"
        mock_private_update.callback_query = mock_callback_query

        await setup_obsidian_git(mock_private_update, mock_context)

        mock_callback_query.edit_message_text.assert_called_once()


class TestProviderMenuViaHub:
    """Test _show_provider_menu called via hub_callback_router."""

    async def test_hub_provider_shows_menu(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Clicking provider button in settings hub shows provider selection menu."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await add_credits("12345", 5)  # PAID tier

        mock_callback_query.data = "hub_provider"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        with patch("src.telegram.handlers.settings.groq_api_key", "test-key"):
            await hub_callback_router(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query.edit_message_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard

        callback_datas = [row[0].callback_data for row in keyboard]
        assert "set_prov_auto" in callback_datas
        assert "set_prov_wit" in callback_datas
        assert "set_prov_groq" in callback_datas

    async def test_hub_provider_menu_without_groq(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Provider menu without Groq key shows only Auto and Wit.ai."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")

        mock_callback_query.data = "hub_provider"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        with patch("src.telegram.handlers.settings.groq_api_key", ""):
            await hub_callback_router(mock_private_update, mock_context)

        call_args = mock_callback_query.edit_message_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard

        callback_datas = [row[0].callback_data for row in keyboard]
        assert "set_prov_auto" in callback_datas
        assert "set_prov_wit" in callback_datas
        assert "set_prov_groq" not in callback_datas

    async def test_provider_menu_marks_current(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Currently selected provider has checkmark."""
        chat_id = "u_12345"
        await set_chat_language(chat_id, "en")
        await set_preferred_provider(chat_id, const.PROVIDER_WIT)

        mock_callback_query.data = "hub_provider"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        with patch("src.telegram.handlers.settings.groq_api_key", "test-key"):
            await hub_callback_router(mock_private_update, mock_context)

        call_args = mock_callback_query.edit_message_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard

        # Wit.ai button should have checkmark
        wit_button = next(row[0] for row in keyboard if "set_prov_wit" in row[0].callback_data)
        assert "\u2705" in wit_button.text

        # Auto button should NOT have checkmark
        auto_button = next(row[0] for row in keyboard if "set_prov_auto" in row[0].callback_data)
        assert "\u2705" not in auto_button.text


class TestEnterCommandFromHub:
    """Test enter_your_command_from_hub callback handler."""

    async def test_returns_waiting_state(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Callback triggers GPT command input mode."""
        mock_callback_query.message.reply_text = AsyncMock()
        mock_private_update.callback_query = mock_callback_query

        result = await enter_your_command_from_hub(mock_private_update, mock_context)

        assert result == WAITING_FOR_COMMAND
        mock_callback_query.answer.assert_called_once()
        mock_callback_query.message.reply_text.assert_called_once()

    async def test_no_query_returns_end(self, mock_private_update, mock_context):
        """Returns END when callback_query is None."""
        mock_private_update.callback_query = None

        result = await enter_your_command_from_hub(mock_private_update, mock_context)

        assert result == ConversationHandler.END


class TestLangButtonsGroupChat:
    """Test lang_buttons in group chat — uses group chat_id prefix."""

    async def test_group_lang_selection(self, mock_group_update, mock_context, mock_callback_query):
        """Language selection in group uses CHAT_PREFIX_GROUP."""
        group_chat_id = -100123456
        chat_id = f"{const.CHAT_PREFIX_GROUP}{group_chat_id}"
        await set_chat_language(chat_id, "en")

        mock_callback_query.data = "set_lang_ru"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = group_chat_id
        mock_group_update.callback_query = mock_callback_query

        mock_context.bot.get_chat_member.return_value = MagicMock(status=ChatMemberStatus.OWNER)

        await lang_buttons(mock_group_update, mock_context)

        mock_callback_query.edit_message_text.assert_called_once()
        assert await get_chat_language(chat_id) == "ru"


class TestHubCallbackUnknownAction:
    """Test hub_callback_router with unknown action — no-op."""

    async def test_unknown_action_does_nothing(
        self, mock_private_update, mock_context, mock_callback_query
    ):
        """Unknown hub_ action is silently ignored."""
        mock_callback_query.data = "hub_nonexistent_action"
        mock_callback_query.from_user.id = 12345
        mock_callback_query.message.chat.id = 12345
        mock_private_update.callback_query = mock_callback_query

        await hub_callback_router(mock_private_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        # No handler called — no further messages
        mock_callback_query.edit_message_text.assert_not_called()


class TestBuildStatsWitStatus:
    """Test build_stats_text with Wit.ai at different usage levels."""

    async def test_wit_warning_threshold(self):
        """Wit.ai at 80% shows Warning status."""
        with (
            patch("src.telegram.handlers.get_monthly_stats", AsyncMock(return_value=None)),
            patch(
                "src.telegram.handlers.get_all_wit_usage_this_month",
                AsyncMock(return_value={"ru": 400}),
            ),
            patch("src.telegram.handlers.settings.wit_free_monthly_limit", 500),
            patch("src.telegram.handlers.settings.groq_api_key", ""),
            patch("src.telegram.handlers.settings.gemini_api_key", ""),
            patch("src.telegram.handlers.settings.anthropic_bot_api_key", ""),
            patch("src.telegram.handlers.settings.openrouter_api_key", ""),
            patch("src.telegram.handlers.settings.gpt_token", ""),
            patch("src.telegram.handlers.settings.groq_audio_daily_limit", 7200),
            patch("src.telegram.handlers.settings.categorization_provider", "deepseek"),
            patch("src.telegram.handlers.settings.gpt_provider", "deepseek"),
            patch("src.telegram.handlers.get_bot_config", AsyncMock(return_value="deepseek")),
        ):
            text = await build_stats_text()

        assert "Warning" in text

    async def test_wit_critical_threshold(self):
        """Wit.ai at 95% shows CRITICAL status."""
        with (
            patch("src.telegram.handlers.get_monthly_stats", AsyncMock(return_value=None)),
            patch(
                "src.telegram.handlers.get_all_wit_usage_this_month",
                AsyncMock(return_value={"ru": 475}),
            ),
            patch("src.telegram.handlers.settings.wit_free_monthly_limit", 500),
            patch("src.telegram.handlers.settings.groq_api_key", ""),
            patch("src.telegram.handlers.settings.gemini_api_key", ""),
            patch("src.telegram.handlers.settings.anthropic_bot_api_key", ""),
            patch("src.telegram.handlers.settings.openrouter_api_key", ""),
            patch("src.telegram.handlers.settings.gpt_token", ""),
            patch("src.telegram.handlers.settings.groq_audio_daily_limit", 7200),
            patch("src.telegram.handlers.settings.categorization_provider", "deepseek"),
            patch("src.telegram.handlers.settings.gpt_provider", "deepseek"),
            patch("src.telegram.handlers.get_bot_config", AsyncMock(return_value="deepseek")),
        ):
            text = await build_stats_text()

        assert "CRITICAL" in text

    async def test_wit_ok_status(self):
        """Wit.ai below 80% shows OK status."""
        with (
            patch("src.telegram.handlers.get_monthly_stats", AsyncMock(return_value=None)),
            patch(
                "src.telegram.handlers.get_all_wit_usage_this_month",
                AsyncMock(return_value={"ru": 100}),
            ),
            patch("src.telegram.handlers.settings.wit_free_monthly_limit", 500),
            patch("src.telegram.handlers.settings.groq_api_key", ""),
            patch("src.telegram.handlers.settings.gemini_api_key", ""),
            patch("src.telegram.handlers.settings.anthropic_bot_api_key", ""),
            patch("src.telegram.handlers.settings.openrouter_api_key", ""),
            patch("src.telegram.handlers.settings.gpt_token", ""),
            patch("src.telegram.handlers.settings.groq_audio_daily_limit", 7200),
            patch("src.telegram.handlers.settings.categorization_provider", "deepseek"),
            patch("src.telegram.handlers.settings.gpt_provider", "deepseek"),
            patch("src.telegram.handlers.get_bot_config", AsyncMock(return_value="deepseek")),
        ):
            text = await build_stats_text()

        assert "OK" in text
        assert "Warning" not in text
        assert "CRITICAL" not in text
