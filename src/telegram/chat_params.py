from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from src import const


def is_private_chat(update: Update) -> bool:
    return update.effective_chat.type == const.PRIVATE_CHAT_TYPE


def get_chat_id(update: Update) -> str:
    if is_private_chat(update):
        return f"{const.CHAT_PREFIX_USER}{update.effective_user.id}"
    else:
        return f"{const.CHAT_PREFIX_GROUP}{update.effective_chat.id}"


async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if is_private_chat(update):
        return True
    else:
        chat_member = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
        )
        return chat_member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)


async def reply_text(update: Update, text: str, **kwargs):
    """Reply via callback query message or regular message."""
    if update.callback_query:
        await update.callback_query.message.reply_text(text, **kwargs)
    else:
        await update.message.reply_text(text, **kwargs)
