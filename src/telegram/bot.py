import typing

from telegram import InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

MAX_TELEGRAM_MESSAGE_LENGTH = 4096

_LINK_PREVIEW_DISABLED = LinkPreviewOptions(is_disabled=True)


async def send_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    response: str,
    keyboard: InlineKeyboardMarkup | None = None,
    **kwargs: typing.Any,
) -> None:
    if update.effective_chat is None:
        return
    chunks = [
        response[i : i + MAX_TELEGRAM_MESSAGE_LENGTH]
        for i in range(0, len(response), MAX_TELEGRAM_MESSAGE_LENGTH)
    ]

    for i, chunk in enumerate(chunks):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=chunk,
            parse_mode=ParseMode.HTML,
            link_preview_options=_LINK_PREVIEW_DISABLED,
            reply_markup=keyboard if i == 0 else None,
            **kwargs,
        )
