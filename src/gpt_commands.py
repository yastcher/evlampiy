import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.ai_client import gpt_chat
from src.telegram.bot import send_response

logger = logging.getLogger(__name__)


async def evlampiy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        gpt_response = await gpt_chat(user_message)

        if not gpt_response:
            await send_response(update, context, response="Empty response from AI")
            return

        await send_response(update, context, response=gpt_response)
    except Exception as e:
        logger.error("Error occurred: %s", e)
        await send_response(update, context, response=str(e))
