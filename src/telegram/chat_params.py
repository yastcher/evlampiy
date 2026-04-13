import typing

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from src import const


def is_bot_sender(update: Update) -> bool:
    """Return True if the update was sent by a Telegram bot account."""
    user = update.effective_user
    return user is not None and user.is_bot


def is_private_chat(update: Update) -> bool:
    if update.effective_chat is None:
        return False
    return update.effective_chat.type == const.PRIVATE_CHAT_TYPE


def get_chat_id(update: Update) -> str:
    if update.effective_chat is None or update.effective_user is None:
        raise ValueError("get_chat_id requires effective_chat and effective_user")
    if is_private_chat(update):
        return f"{const.CHAT_PREFIX_USER}{update.effective_user.id}"
    else:
        return f"{const.CHAT_PREFIX_GROUP}{update.effective_chat.id}"


async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat is None or update.effective_user is None:
        return False
    if is_private_chat(update):
        return True
    else:
        chat_member = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
        )
        return chat_member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)


async def reply_text(update: Update, text: str, **kwargs: typing.Any) -> None:
    """Reply via callback query message or regular message."""
    if update.callback_query:
        msg = update.callback_query.message
        if msg is None:  # pragma: no cover
            return
        await msg.reply_text(text, **kwargs)  # ty: ignore[unresolved-attribute]
    else:
        if update.message is None:
            return
        await update.message.reply_text(text, **kwargs)
