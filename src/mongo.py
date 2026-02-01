from beanie import init_beanie
from motor import motor_asyncio

from src.config import settings
from src.dto import (
    AccountLink,
    AlertState,
    LinkAttempt,
    LinkCode,
    MonthlyStats,
    UsedTrial,
    UserCredits,
    UserSettings,
    WitUsageStats,
)

ALL_DOCUMENT_MODELS = [UserSettings, UserCredits, UsedTrial, WitUsageStats, MonthlyStats, AlertState, AccountLink, LinkCode, LinkAttempt]


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
