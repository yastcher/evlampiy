"""Notes / Obsidian use-case service. Framework-agnostic — no aiogram/pywa."""

from src.categorization import categorize_all_inbox
from src.mongo import (
    get_auto_categorize,
    get_github_settings,
    get_save_to_obsidian,
    set_auto_categorize,
    set_save_to_obsidian,
)
from src.types import ChatId


async def toggle_save_to_obsidian(chat_id: ChatId) -> bool:
    """Flip the save-to-Obsidian flag and return the new value."""
    new_value = not await get_save_to_obsidian(chat_id)
    await set_save_to_obsidian(chat_id, new_value)
    return new_value


async def toggle_auto_categorize(chat_id: ChatId) -> bool:
    """Flip the auto-categorize flag and return the new value."""
    new_value = not await get_auto_categorize(chat_id)
    await set_auto_categorize(chat_id, new_value)
    return new_value


async def categorize_all_for_chat(chat_id: ChatId) -> tuple[bool, int]:
    """Run categorization for a chat's GitHub repo.

    Returns ``(has_repo, count)``. ``has_repo=False`` means the chat hasn't connected
    GitHub yet — caller decides what to tell the user. ``count=0`` is a successful run
    where there were no inbox files to categorize.
    """
    repo_info = await get_github_settings(chat_id)
    if not repo_info:
        return False, 0
    count = await categorize_all_inbox(repo_info)
    return True, count
