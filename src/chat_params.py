from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from telegram import Update


def is_private_chat(update: Update) -> bool:
    return update.effective_chat.type == "private"


def get_chat_id(update: Update) -> str:
    if is_private_chat(update):
        return f"u_{update.effective_user.id}"
    else:
        return f"g_{update.effective_chat.id}"


async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if is_private_chat(update):
        return True
    else:
        chat_member = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id,
        )
        return chat_member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)
