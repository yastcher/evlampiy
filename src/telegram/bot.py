import typing

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, LinkPreviewOptions, Message

from src.telegram.chat_params import EventLike

MAX_TELEGRAM_MESSAGE_LENGTH = 4096

_LINK_PREVIEW_DISABLED = LinkPreviewOptions(is_disabled=True)


def _resolve_chat_id(event: EventLike) -> int | None:
    if isinstance(event, Message):
        return event.chat.id
    if event.message is not None:
        return event.message.chat.id
    return None


async def send_response(
    event: EventLike,
    bot: Bot,
    response: str,
    keyboard: InlineKeyboardMarkup | None = None,
    **kwargs: typing.Any,
) -> None:
    chat_id = _resolve_chat_id(event)
    if chat_id is None:
        return
    chunks = [
        response[i : i + MAX_TELEGRAM_MESSAGE_LENGTH]
        for i in range(0, len(response), MAX_TELEGRAM_MESSAGE_LENGTH)
    ]

    for i, chunk in enumerate(chunks):
        await bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode=ParseMode.HTML,
            link_preview_options=_LINK_PREVIEW_DISABLED,
            reply_markup=keyboard if i == 0 else None,
            **kwargs,
        )


__all__ = ["MAX_TELEGRAM_MESSAGE_LENGTH", "CallbackQuery", "send_response"]
