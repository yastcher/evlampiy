from beanie import init_beanie
from motor import motor_asyncio

from src.config import settings
from src.dto import (
    AccountLink,
    AlertState,
    BotConfig,
    LinkAttempt,
    LinkCode,
    MonthlyStats,
    RecentTranscription,
    UsedTrial,
    UserCredits,
    UserMonthlyUsage,
    UserRole,
    UserSettings,
    WitUsageStats,
)

ALL_DOCUMENT_MODELS = [
    UserSettings,
    UserCredits,
    UsedTrial,
    WitUsageStats,
    MonthlyStats,
    AlertState,
    UserRole,
    AccountLink,
    LinkCode,
    LinkAttempt,
    UserMonthlyUsage,
    RecentTranscription,
    BotConfig,
]


async def init_beanie_models():
    """
    to call only once
    """
    mongo_client = motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(database=mongo_client["user_settings"], document_models=ALL_DOCUMENT_MODELS)


async def get_or_create_user(chat_id: str) -> UserSettings:
    """Get existing user or create new one with defaults."""
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        user = UserSettings(chat_id=chat_id)
        await user.insert()
    return user


async def set_chat_language(chat_id: str, language: str):
    user = await get_or_create_user(chat_id)
    user.language = language
    await user.save()


async def get_chat_language(chat_id: str) -> str:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return settings.default_language
    return user.language or settings.default_language


async def set_gpt_command(chat_id: str, command: str):
    user = await get_or_create_user(chat_id)
    user.command = command
    await user.save()


async def get_gpt_command(chat_id: str) -> str:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return settings.telegram_bot_command
    return user.command or settings.telegram_bot_command


async def set_github_settings(chat_id: str, owner: str, repo: str, token: str):
    user = await get_or_create_user(chat_id)
    user.github_settings = {
        "owner": owner,
        "repo": repo,
        "token": token,
    }
    await user.save()


async def get_github_settings(chat_id: str) -> dict:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user or not user.github_settings:
        return {}
    if all(user.github_settings.values()):
        return user.github_settings
    return {}


async def clear_github_settings(chat_id: str):
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if user:
        user.github_settings = None
        user.save_to_obsidian = False
        await user.save()


async def set_save_to_obsidian(chat_id: str, enabled: bool):
    user = await get_or_create_user(chat_id)
    user.save_to_obsidian = enabled
    await user.save()


async def get_save_to_obsidian(chat_id: str) -> bool:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return False
    return user.save_to_obsidian


async def set_auto_categorize(chat_id: str, enabled: bool):
    user = await get_or_create_user(chat_id)
    user.auto_categorize = enabled
    await user.save()


async def get_auto_categorize(chat_id: str) -> bool:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return False
    return user.auto_categorize


async def set_auto_cleanup(chat_id: str, enabled: bool):
    user = await get_or_create_user(chat_id)
    user.auto_cleanup = enabled
    await user.save()


async def get_auto_cleanup(chat_id: str) -> bool:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return False
    return user.auto_cleanup


async def set_preferred_provider(chat_id: str, provider: str | None):
    user = await get_or_create_user(chat_id)
    user.preferred_provider = provider
    await user.save()


async def get_preferred_provider(chat_id: str) -> str | None:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return None
    return user.preferred_provider


async def add_user_role(user_id: str, role: str, added_by: str):
    """Add a role to a user (upsert)."""
    existing = await UserRole.find_one(UserRole.user_id == user_id, UserRole.role == role)
    if existing:
        return
    await UserRole(user_id=user_id, role=role, added_by=added_by).insert()


async def remove_user_role(user_id: str, role: str) -> bool:
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


async def has_role(user_id: str, role: str) -> bool:
    """Check if a user has a specific role."""
    existing = await UserRole.find_one(UserRole.user_id == user_id, UserRole.role == role)
    return existing is not None


_RECENT_TRANSCRIPTION_KEEP = 5


async def save_recent_transcription(chat_id: str, text: str) -> None:
    """Save cleaned transcription for cleanup context; keep only the last 5 per chat."""
    await RecentTranscription(chat_id=chat_id, text=text).insert()
    # Trim to keep only the most recent entries
    all_docs = (
        await RecentTranscription.find(RecentTranscription.chat_id == chat_id)
        .sort("-created_at")
        .to_list()
    )
    for doc in all_docs[_RECENT_TRANSCRIPTION_KEEP:]:
        await doc.delete()


async def get_recent_transcriptions(chat_id: str, limit: int = 3) -> list[str]:
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
    doc = await BotConfig.find_one(BotConfig.key == key)
    if doc:
        doc.value = value
        await doc.save()
    else:
        await BotConfig(key=key, value=value).insert()
