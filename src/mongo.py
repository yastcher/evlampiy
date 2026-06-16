import contextlib
import typing

import pymongo.errors
from beanie import Document, init_beanie
from motor import motor_asyncio

from src.config import settings
from src.dto import (
    AccountLink,
    AlertState,
    BotConfig,
    LinkAttempt,
    LinkCode,
    MonthlyStats,
    ProcessedPayment,
    RecentTranscription,
    UsedTrial,
    UserCredits,
    UserMonthlyUsage,
    UserRole,
    UserSettings,
    WitUsageStats,
)
from src.github_api import GitHubRepo
from src.types import ChatId, Language, UserId

ALL_DOCUMENT_MODELS = [
    UserSettings,
    UserCredits,
    UsedTrial,
    WitUsageStats,
    MonthlyStats,
    ProcessedPayment,
    AlertState,
    UserRole,
    AccountLink,
    LinkCode,
    LinkAttempt,
    UserMonthlyUsage,
    RecentTranscription,
    BotConfig,
]


async def init_beanie_models() -> None:
    """
    to call only once
    """
    mongo_client: typing.Any = motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(database=mongo_client["user_settings"], document_models=ALL_DOCUMENT_MODELS)  # ty: ignore[invalid-argument-type]


async def get_or_create[DocT: Document](
    finder: typing.Callable[[], typing.Awaitable[DocT | None]],
    factory: typing.Callable[[], DocT],
) -> DocT:
    """Return an existing document or create it, surviving a concurrent-insert race.

    With a unique index on the natural key, two requests creating the same document
    concurrently have one insert win; the loser's insert raises DuplicateKeyError, which
    we swallow and re-fetch the winner — so callers never observe duplicates or the race.
    """
    existing = await finder()
    if existing is not None:
        return existing
    try:
        doc = factory()
        await doc.insert()
        return doc
    except pymongo.errors.DuplicateKeyError:
        winner = await finder()
        if winner is None:
            raise
        return winner


async def get_or_create_user(chat_id: ChatId) -> UserSettings:
    """Get existing user or create new one with defaults."""
    return await get_or_create(
        lambda: UserSettings.find_one(UserSettings.chat_id == chat_id),
        lambda: UserSettings(chat_id=chat_id),
    )


async def set_chat_language(chat_id: ChatId, language: Language) -> None:
    user = await get_or_create_user(chat_id)
    user.language = language
    await user.save()


async def get_chat_language(chat_id: ChatId) -> str:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return settings.default_language
    return user.language or settings.default_language


async def set_gpt_command(chat_id: ChatId, command: str) -> None:
    user = await get_or_create_user(chat_id)
    user.command = command
    await user.save()


async def get_gpt_command(chat_id: ChatId) -> str:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return settings.telegram_bot_command
    return user.command or settings.telegram_bot_command


async def set_github_settings(chat_id: ChatId, owner: str, repo: str, token: str) -> None:
    user = await get_or_create_user(chat_id)
    user.github_settings = {
        "owner": owner,
        "repo": repo,
        "token": token,
    }
    await user.save()


async def get_github_settings(chat_id: ChatId) -> GitHubRepo | None:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user or not user.github_settings:
        return None
    if all(user.github_settings.values()):
        return GitHubRepo(
            token=user.github_settings["token"],
            owner=user.github_settings["owner"],
            repo=user.github_settings["repo"],
        )
    return None


async def clear_github_settings(chat_id: ChatId) -> None:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if user:
        user.github_settings = None
        user.save_to_obsidian = False
        await user.save()


async def set_save_to_obsidian(chat_id: ChatId, enabled: bool) -> None:
    user = await get_or_create_user(chat_id)
    user.save_to_obsidian = enabled
    await user.save()


async def get_save_to_obsidian(chat_id: ChatId) -> bool:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return False
    return user.save_to_obsidian


async def set_auto_categorize(chat_id: ChatId, enabled: bool) -> None:
    user = await get_or_create_user(chat_id)
    user.auto_categorize = enabled
    await user.save()


async def get_auto_categorize(chat_id: ChatId) -> bool:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return False
    return user.auto_categorize


async def set_auto_cleanup(chat_id: ChatId, enabled: bool) -> None:
    user = await get_or_create_user(chat_id)
    user.auto_cleanup = enabled
    await user.save()


async def get_auto_cleanup(chat_id: ChatId) -> bool:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return False
    return user.auto_cleanup


async def set_preferred_provider(chat_id: ChatId, provider: str | None) -> None:
    user = await get_or_create_user(chat_id)
    user.preferred_provider = provider
    await user.save()


async def get_preferred_provider(chat_id: ChatId) -> str | None:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return None
    return user.preferred_provider


async def add_user_role(user_id: UserId, role: str, added_by: str) -> None:
    """Add a role to a user (idempotent)."""
    existing = await UserRole.find_one(UserRole.user_id == user_id, UserRole.role == role)
    if existing:
        return
    # Concurrent add of the same role may win the race — already present, ignore.
    with contextlib.suppress(pymongo.errors.DuplicateKeyError):
        await UserRole(user_id=user_id, role=role, added_by=added_by).insert()


async def remove_user_role(user_id: UserId, role: str) -> bool:
    """Remove a role from a user. Returns True if removed."""
    existing = await UserRole.find_one(UserRole.user_id == user_id, UserRole.role == role)
    if not existing:
        return False
    await existing.delete()
    return True


async def get_users_by_role(role: str) -> list[str]:
    """Get all user IDs with a given role."""
    docs = await UserRole.find(UserRole.role == role).to_list()
    return [doc.user_id for doc in docs]


async def has_role(user_id: UserId, role: str) -> bool:
    """Check if a user has a specific role."""
    existing = await UserRole.find_one(UserRole.user_id == user_id, UserRole.role == role)
    return existing is not None


_RECENT_TRANSCRIPTION_KEEP = 5


async def save_recent_transcription(chat_id: ChatId, text: str) -> None:
    """Save cleaned transcription for cleanup context; keep only the last 5 per chat."""
    await RecentTranscription(chat_id=chat_id, text=text).insert()
    # Trim to keep only the most recent entries
    all_docs = await RecentTranscription.find(RecentTranscription.chat_id == chat_id).sort("-created_at").to_list()
    for doc in all_docs[_RECENT_TRANSCRIPTION_KEEP:]:
        await doc.delete()


async def get_recent_transcriptions(chat_id: ChatId, limit: int = 3) -> list[str]:
    """Get recent cleaned transcriptions for a chat, oldest-first (for LLM context)."""
    docs = (
        await RecentTranscription.find(RecentTranscription.chat_id == chat_id)
        .sort("-created_at")
        .limit(limit)
        .to_list()
    )
    return [doc.text for doc in reversed(docs)]


async def get_bot_config(key: str, default: str = "") -> str:
    """Get a runtime bot config value; falls back to default if not set."""
    doc = await BotConfig.find_one(BotConfig.key == key)
    return doc.value if doc else default


async def set_bot_config(key: str, value: str) -> None:
    """Set a runtime bot config value (upsert)."""
    doc = await get_or_create(
        lambda: BotConfig.find_one(BotConfig.key == key),
        lambda: BotConfig(key=key, value=value),
    )
    if doc.value != value:
        doc.value = value
        await doc.save()
