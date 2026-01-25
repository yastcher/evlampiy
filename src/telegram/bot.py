from typing import Optional

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

MAX_TELEGRAM_MESSAGE_LENGTH = 4096


async def send_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    response: str,
    keyboard: Optional[InlineKeyboardMarkup] = None,
    **kwargs,
) -> None:
    chunks = [
        response[i : i + MAX_TELEGRAM_MESSAGE_LENGTH]
        for i in range(0, len(response), MAX_TELEGRAM_MESSAGE_LENGTH)
    ]

    for i, chunk in enumerate(chunks):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=chunk,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=keyboard if i == 0 else None,
            **kwargs,
        )
