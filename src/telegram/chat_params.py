import typing

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.types import CallbackQuery, Chat, Message, User

from src import const

EventLike = Message | CallbackQuery


def _event_user(event: EventLike) -> User | None:
    return event.from_user


def _event_chat(event: EventLike) -> Chat | None:
    if isinstance(event, Message):
        return event.chat
    if event.message is not None:
        return event.message.chat
    return None


def is_bot_sender(event: EventLike) -> bool:
    """Return True if the event was sent by a Telegram bot account."""
    user = _event_user(event)
    return user is not None and user.is_bot


def is_private_chat(event: EventLike) -> bool:
    chat = _event_chat(event)
    if chat is None:
        return False
    return chat.type == const.PRIVATE_CHAT_TYPE


def get_chat_id(event: EventLike) -> str:
    chat = _event_chat(event)
    user = _event_user(event)
    if chat is None or user is None:
        raise ValueError("get_chat_id requires chat and user on the event")
    if is_private_chat(event):
        return f"{const.CHAT_PREFIX_USER}{user.id}"
    return f"{const.CHAT_PREFIX_GROUP}{chat.id}"


async def is_user_admin(event: EventLike, bot: Bot) -> bool:
    chat = _event_chat(event)
    user = _event_user(event)
    if chat is None or user is None:
        return False
    if is_private_chat(event):
        return True
    chat_member = await bot.get_chat_member(chat_id=chat.id, user_id=user.id)
    return chat_member.status in (ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR)


async def reply_text(event: EventLike, text: str, **kwargs: typing.Any) -> None:
    """Reply via callback query message or regular message."""
    if isinstance(event, CallbackQuery):
        msg = event.message
        if not isinstance(msg, Message):  # pragma: no cover
            return
        await msg.answer(text, **kwargs)
    else:
        await event.answer(text, **kwargs)
