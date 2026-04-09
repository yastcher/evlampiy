"""GPT chat command handler with tool calling support."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.ai_client import GPT_FALLBACK_CHAIN
from src.config import settings
from src.mongo import get_bot_config
from src.prompts import GPT_SYSTEM_PROMPT
from src.telegram.bot import send_response
from src.telegram.chat_params import get_chat_id
from src.tool_calling import run_tool_conversation
from src.tools import get_tools

logger = logging.getLogger(__name__)


async def evlampiy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    user_message = update.message.text or ""
    chat_id = get_chat_id(update)

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
            await send_response(update, context, response="Empty response from AI")
            return

        await send_response(update, context, response=gpt_response)
    except Exception as e:
        logger.error("Error occurred: %s", e)
        await send_response(update, context, response=str(e))
