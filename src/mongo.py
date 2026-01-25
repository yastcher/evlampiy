from beanie import init_beanie
from motor import motor_asyncio

from src.config import settings
from src.dto import UserSettings


async def init_beanie_models():
    """
    to call only once
    """
    mongo_client = motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(database=mongo_client["user_settings"], document_models=[UserSettings])


async def set_chat_language(chat_id: str, language: str):
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        user = UserSettings(chat_id=chat_id, language=language)
        await user.insert()
    else:
        user.language = language
        await user.save()


async def get_chat_language(chat_id: str) -> str:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return settings.default_language
    return user.language or settings.default_language


async def set_gpt_command(chat_id: str, command: str):
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        user = UserSettings(chat_id=chat_id, command=command)
        await user.insert()
    else:
        user.command = command
        await user.save()


async def get_gpt_command(chat_id: str) -> str:
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        return settings.telegram_bot_command
    return user.command or settings.telegram_bot_command


async def set_github_settings(chat_id: str, owner: str, repo: str, token: str):
    user = await UserSettings.find_one(UserSettings.chat_id == chat_id)
    if not user:
        user = UserSettings(
            chat_id=chat_id,
            github_settings={
                "owner": owner,
                "repo": repo,
                "token": token,
            },
        )
        await user.insert()
    else:
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
