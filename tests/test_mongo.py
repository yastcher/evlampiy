import pytest

from src.config import settings
from src.dto import UserSettings
from src.mongo import (
    clear_github_settings,
    get_chat_language,
    get_github_settings,
    get_gpt_command,
    get_save_to_obsidian,
    set_chat_language,
    set_github_settings,
    set_gpt_command,
    set_save_to_obsidian,
)

pytestmark = [pytest.mark.asyncio]


class TestChatLanguage:
    """Test language CRUD operations."""

    async def test_get_language_returns_default_for_new_user(self):
        """New user should get default language."""
        result = await get_chat_language("u_new_user")
        assert result == settings.default_language

    async def test_set_and_get_language_for_new_user(self):
        """Setting language for new user creates record."""
        await set_chat_language("u_12345", "en")
        result = await get_chat_language("u_12345")
        assert result == "en"

    async def test_update_language_for_existing_user(self):
        """Updating language for existing user."""
        await set_chat_language("u_12345", "en")
        await set_chat_language("u_12345", "de")
        result = await get_chat_language("u_12345")
        assert result == "de"

    async def test_get_language_returns_default_when_null(self):
        """User with null language field should get default."""
        user = UserSettings(chat_id="u_null_lang", language=None)
        await user.insert()
        result = await get_chat_language("u_null_lang")
        assert result == settings.default_language


class TestGptCommand:
    """Test GPT command CRUD operations."""

    async def test_get_command_returns_default_for_new_user(self):
        """New user should get default command."""
        result = await get_gpt_command("u_new_user")
        assert result == settings.telegram_bot_command

    async def test_set_and_get_command_for_new_user(self):
        """Setting command for new user creates record."""
        await set_gpt_command("u_12345", "custom_command")
        result = await get_gpt_command("u_12345")
        assert result == "custom_command"

    async def test_update_command_for_existing_user(self):
        """Updating command for existing user."""
        await set_gpt_command("u_12345", "first")
        await set_gpt_command("u_12345", "second")
        result = await get_gpt_command("u_12345")
        assert result == "second"

    async def test_get_command_returns_default_when_null(self):
        """User with null command field should get default."""
        user = UserSettings(chat_id="u_null_cmd", command=None)
        await user.insert()
        result = await get_gpt_command("u_null_cmd")
        assert result == settings.telegram_bot_command


class TestGithubSettings:
    """Test GitHub settings CRUD operations."""

    async def test_get_github_returns_empty_for_new_user(self):
        """New user should get empty dict."""
        result = await get_github_settings("u_new_user")
        assert result == {}

    async def test_set_and_get_github_settings(self):
        """Setting GitHub settings for new user."""
        await set_github_settings("u_12345", "owner", "repo", "token123")
        result = await get_github_settings("u_12345")
        assert result == {"owner": "owner", "repo": "repo", "token": "token123"}

    async def test_update_github_settings(self):
        """Updating GitHub settings for existing user."""
        await set_github_settings("u_12345", "old_owner", "old_repo", "old_token")
        await set_github_settings("u_12345", "new_owner", "new_repo", "new_token")
        result = await get_github_settings("u_12345")
        assert result == {"owner": "new_owner", "repo": "new_repo", "token": "new_token"}

    async def test_get_github_returns_empty_when_null(self):
        """User with null github_settings should get empty dict."""
        user = UserSettings(chat_id="u_null_gh", github_settings=None)
        await user.insert()
        result = await get_github_settings("u_null_gh")
        assert result == {}

    async def test_get_github_returns_empty_when_incomplete(self):
        """User with incomplete github_settings should get empty dict."""
        user = UserSettings(
            chat_id="u_incomplete",
            github_settings={"owner": "test", "repo": "", "token": "abc"},
        )
        await user.insert()
        result = await get_github_settings("u_incomplete")
        assert result == {}

    async def test_clear_github_settings(self):
        """Clearing GitHub settings also disables save_to_obsidian."""
        await set_github_settings("u_12345", "owner", "repo", "token")
        await set_save_to_obsidian("u_12345", True)
        await clear_github_settings("u_12345")
        result = await get_github_settings("u_12345")
        assert result == {}
        assert await get_save_to_obsidian("u_12345") is False

    async def test_clear_github_settings_no_user(self):
        """Clearing settings for nonexistent user does nothing."""
        await clear_github_settings("u_nonexistent")


class TestSaveToObsidian:
    """Test save_to_obsidian CRUD operations."""

    async def test_get_returns_false_for_new_user(self):
        """New user should have save_to_obsidian=False."""
        result = await get_save_to_obsidian("u_new_user")
        assert result is False

    async def test_set_and_get(self):
        """Setting save_to_obsidian for user."""
        await set_save_to_obsidian("u_12345", True)
        result = await get_save_to_obsidian("u_12345")
        assert result is True

    async def test_toggle_off(self):
        """Disabling save_to_obsidian."""
        await set_save_to_obsidian("u_12345", True)
        await set_save_to_obsidian("u_12345", False)
        result = await get_save_to_obsidian("u_12345")
        assert result is False

    async def test_default_value_for_existing_user(self):
        """Existing user without explicit setting should have False."""
        user = UserSettings(chat_id="u_existing")
        await user.insert()
        result = await get_save_to_obsidian("u_existing")
        assert result is False
