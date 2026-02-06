"""Integration test for complete user settings lifecycle."""

from src.config import settings
from src.dto import UserSettings
from src.mongo import (
    clear_github_settings,
    get_auto_categorize,
    get_chat_language,
    get_github_settings,
    get_gpt_command,
    get_save_to_obsidian,
    set_auto_categorize,
    set_chat_language,
    set_github_settings,
    set_gpt_command,
    set_save_to_obsidian,
)


class TestUserSettingsLifecycle:
    """Full user settings lifecycle integration test."""

    async def test_complete_settings_flow(self):
        """Test complete user settings journey."""
        chat_id = "u_lifecycle_test"

        # 1. New user gets defaults
        assert await get_chat_language(chat_id) == settings.default_language
        assert await get_gpt_command(chat_id) == settings.telegram_bot_command
        assert await get_github_settings(chat_id) == {}
        assert await get_save_to_obsidian(chat_id) is False

        # 2. Set language
        await set_chat_language(chat_id, "en")
        assert await get_chat_language(chat_id) == "en"

        # 3. Update language
        await set_chat_language(chat_id, "de")
        assert await get_chat_language(chat_id) == "de"

        # 4. Set GPT command
        await set_gpt_command(chat_id, "assistant")
        assert await get_gpt_command(chat_id) == "assistant"

        # 5. Update GPT command
        await set_gpt_command(chat_id, "helper")
        assert await get_gpt_command(chat_id) == "helper"

        # 6. Set GitHub settings
        await set_github_settings(chat_id, "testowner", "testrepo", "ghp_token123")
        github = await get_github_settings(chat_id)
        assert github == {"owner": "testowner", "repo": "testrepo", "token": "ghp_token123"}

        # 7. Enable Obsidian sync
        await set_save_to_obsidian(chat_id, True)
        assert await get_save_to_obsidian(chat_id) is True

        # 8. Update GitHub settings
        await set_github_settings(chat_id, "newowner", "newrepo", "ghp_newtoken")
        github = await get_github_settings(chat_id)
        assert github == {"owner": "newowner", "repo": "newrepo", "token": "ghp_newtoken"}

        # 9. Toggle Obsidian off
        await set_save_to_obsidian(chat_id, False)
        assert await get_save_to_obsidian(chat_id) is False

        # 10. Clear GitHub settings (also disables Obsidian)
        await set_save_to_obsidian(chat_id, True)
        await clear_github_settings(chat_id)
        assert await get_github_settings(chat_id) == {}
        assert await get_save_to_obsidian(chat_id) is False

        # 11. Other settings remain intact after GitHub clear
        assert await get_chat_language(chat_id) == "de"
        assert await get_gpt_command(chat_id) == "helper"

    async def test_null_fields_return_defaults(self):
        """User with null fields gets default values."""
        chat_id = "u_null_fields"
        user = UserSettings(chat_id=chat_id, language=None, command=None, github_settings=None)
        await user.insert()

        assert await get_chat_language(chat_id) == settings.default_language
        assert await get_gpt_command(chat_id) == settings.telegram_bot_command
        assert await get_github_settings(chat_id) == {}
        assert await get_save_to_obsidian(chat_id) is False

    async def test_incomplete_github_settings_return_empty(self):
        """Incomplete GitHub settings return empty dict."""
        chat_id = "u_incomplete_gh"
        user = UserSettings(
            chat_id=chat_id,
            github_settings={"owner": "test", "repo": "", "token": "abc"},
        )
        await user.insert()

        assert await get_github_settings(chat_id) == {}

    async def test_clear_nonexistent_user_no_error(self):
        """Clearing settings for nonexistent user does nothing."""
        await clear_github_settings("u_nonexistent_12345")

    async def test_auto_categorize_lifecycle(self):
        """Test auto_categorize setting lifecycle."""
        chat_id = "u_categorize_test"

        # New user gets default (False)
        assert await get_auto_categorize(chat_id) is False

        # Enable auto_categorize for new user
        await set_auto_categorize(chat_id, True)
        assert await get_auto_categorize(chat_id) is True

        # Disable auto_categorize
        await set_auto_categorize(chat_id, False)
        assert await get_auto_categorize(chat_id) is False

        # Re-enable
        await set_auto_categorize(chat_id, True)
        assert await get_auto_categorize(chat_id) is True
