"""GPT chat command handler with tool calling support."""

import logging

from aiogram import Bot
from aiogram.types import Message

from evlampiy.ai_client import GPT_FALLBACK_CHAIN
from evlampiy.config import settings
from evlampiy.localization import translates
from evlampiy.mongo import get_bot_config, get_chat_language
from evlampiy.prompts import GPT_SYSTEM_PROMPT
from evlampiy.telegram.bot import send_response
from evlampiy.telegram.chat_params import get_chat_id, is_blocked_sender
from evlampiy.tool_calling import run_tool_conversation
from evlampiy.tools import get_tools

logger = logging.getLogger(__name__)


async def evlampiy_command(message: Message, bot: Bot) -> None:
    user_message = message.text or ""
    chat_id = get_chat_id(message)
    if await is_blocked_sender(message):
        language = await get_chat_language(chat_id)
        await send_response(
            message, bot, response=translates["blocked_message"].get(language, translates["blocked_message"]["en"])
        )
        return

    try:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": GPT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        tools = get_tools(chat_id)

        primary = await get_bot_config("gpt_provider", settings.gpt_provider)
        chain = [primary] + [p for p in GPT_FALLBACK_CHAIN if p != primary]

        gpt_response = await run_tool_conversation(messages, tools, chain)

        if not gpt_response:
            await send_response(message, bot, response="Empty response from AI")
            return

        await send_response(message, bot, response=gpt_response)
    except Exception as e:
        logger.error("Error occurred: %s", e)
        await send_response(message, bot, response=str(e))
