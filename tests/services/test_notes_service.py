"""Tests for src.services.notes_service."""

from unittest.mock import AsyncMock, patch

from src.mongo import (
    get_auto_categorize,
    get_save_to_obsidian,
    set_auto_categorize,
    set_github_settings,
    set_save_to_obsidian,
)
from src.services.notes_service import (
    categorize_all_for_chat,
    toggle_auto_categorize,
    toggle_save_to_obsidian,
)


class TestToggleSaveToObsidian:
    async def test_off_to_on(self):
        chat_id = "u_notes_1"
        await set_save_to_obsidian(chat_id, False)
        assert await toggle_save_to_obsidian(chat_id) is True
        assert await get_save_to_obsidian(chat_id) is True

    async def test_on_to_off(self):
        chat_id = "u_notes_2"
        await set_save_to_obsidian(chat_id, True)
        assert await toggle_save_to_obsidian(chat_id) is False
        assert await get_save_to_obsidian(chat_id) is False


class TestToggleAutoCategorize:
    async def test_off_to_on(self):
        chat_id = "u_notes_3"
        await set_auto_categorize(chat_id, False)
        assert await toggle_auto_categorize(chat_id) is True
        assert await get_auto_categorize(chat_id) is True

    async def test_on_to_off(self):
        chat_id = "u_notes_4"
        await set_auto_categorize(chat_id, True)
        assert await toggle_auto_categorize(chat_id) is False
        assert await get_auto_categorize(chat_id) is False


class TestCategorizeAllForChat:
    async def test_no_repo_returns_false_zero(self):
        has_repo, count = await categorize_all_for_chat("u_notes_5")
        assert has_repo is False
        assert count == 0

    async def test_with_repo_runs_categorize(self):
        chat_id = "u_notes_6"
        await set_github_settings(chat_id, "owner", "repo", "tok")
        with patch(
            "src.services.notes_service.categorize_all_inbox",
            AsyncMock(return_value=7),
        ) as mock_cat:
            has_repo, count = await categorize_all_for_chat(chat_id)
        assert has_repo is True
        assert count == 7
        mock_cat.assert_called_once()
