"""Admin Telegram handlers for managing VIP/tester/blocked users."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src import const
from src.credits import admin_add_credits, is_admin_user
from src.localization import translates
from src.mongo import add_user_role, get_users_by_role, remove_user_role
from src.telegram.handlers import stats_command

logger = logging.getLogger(__name__)

ADMIN_LANG = "en"


def _t(key: str, **kwargs) -> str:
    """Get admin translation (always English for admin interface)."""
    text = translates[key].get(ADMIN_LANG, translates[key]["en"])
    if kwargs:
        return text.format(**kwargs)
    return text


def _parse_user_id(args: list[str]) -> str | None:
    """Extract and validate user_id from command arguments."""
    if not args:
        return None
    user_id = args[0].strip()
    if not user_id.isdigit():
        return None
    return user_id


async def admin_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel with inline keyboard."""
    if not is_admin_user(str(update.effective_user.id)):
        return

    keyboard = [
        [InlineKeyboardButton(_t("btn_manage_vip"), callback_data="adm_vip")],
        [InlineKeyboardButton(_t("btn_manage_testers"), callback_data="adm_testers")],
        [InlineKeyboardButton(_t("btn_manage_blocked"), callback_data="adm_blocked")],
        [InlineKeyboardButton(_t("btn_admin_stats"), callback_data="adm_stats")],
        [InlineKeyboardButton(_t("btn_add_credits"), callback_data="adm_credits")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(_t("admin_hub_title"), reply_markup=reply_markup)


async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route admin hub button presses."""
    if not is_admin_user(str(update.effective_user.id)):
        return

    query = update.callback_query
    await query.answer()

    action = query.data.replace("adm_", "")

    if action == "vip":
        users = await get_users_by_role(const.ROLE_VIP)
        user_list = "\n".join(f"• {uid}" for uid in users) if users else _t("admin_list_empty")
        text = _t("admin_vip_list", users=user_list)
        await query.edit_message_text(text, parse_mode="HTML")

    elif action == "testers":
        users = await get_users_by_role(const.ROLE_TESTER)
        user_list = "\n".join(f"• {uid}" for uid in users) if users else _t("admin_list_empty")
        text = _t("admin_tester_list", users=user_list)
        await query.edit_message_text(text, parse_mode="HTML")

    elif action == "blocked":
        users = await get_users_by_role(const.ROLE_BLOCKED)
        user_list = "\n".join(f"• {uid}" for uid in users) if users else _t("admin_list_empty")
        text = _t("admin_blocked_list", users=user_list)
        await query.edit_message_text(text, parse_mode="HTML")

    elif action == "stats":
        await stats_command(update, context)

    elif action == "credits":
        text = _t("admin_usage", command="/add_credits <user_id> <amount>")
        await query.edit_message_text(text)


async def add_vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a user to VIP list. Usage: /add_vip <user_id>"""
    if not is_admin_user(str(update.effective_user.id)):
        return

    user_id = _parse_user_id(context.args)
    if not user_id:
        await update.message.reply_text(_t("admin_usage", command="/add_vip <user_id>"))
        return

    admin_id = str(update.effective_user.id)
    await add_user_role(user_id, const.ROLE_VIP, admin_id)
    await update.message.reply_text(_t("admin_user_added", user_id=user_id, role="VIP"))


async def remove_vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user from VIP list. Usage: /remove_vip <user_id>"""
    if not is_admin_user(str(update.effective_user.id)):
        return

    user_id = _parse_user_id(context.args)
    if not user_id:
        await update.message.reply_text(_t("admin_usage", command="/remove_vip <user_id>"))
        return

    removed = await remove_user_role(user_id, const.ROLE_VIP)
    if removed:
        await update.message.reply_text(_t("admin_user_removed", user_id=user_id, role="VIP"))
    else:
        await update.message.reply_text(_t("admin_user_not_found", user_id=user_id, role="VIP"))


async def add_tester_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a user to tester list. Usage: /add_tester <user_id>"""
    if not is_admin_user(str(update.effective_user.id)):
        return

    user_id = _parse_user_id(context.args)
    if not user_id:
        await update.message.reply_text(_t("admin_usage", command="/add_tester <user_id>"))
        return

    admin_id = str(update.effective_user.id)
    await add_user_role(user_id, const.ROLE_TESTER, admin_id)
    await update.message.reply_text(_t("admin_user_added", user_id=user_id, role="tester"))


async def remove_tester_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a user from tester list. Usage: /remove_tester <user_id>"""
    if not is_admin_user(str(update.effective_user.id)):
        return

    user_id = _parse_user_id(context.args)
    if not user_id:
        await update.message.reply_text(_t("admin_usage", command="/remove_tester <user_id>"))
        return

    removed = await remove_user_role(user_id, const.ROLE_TESTER)
    if removed:
        await update.message.reply_text(_t("admin_user_removed", user_id=user_id, role="tester"))
    else:
        await update.message.reply_text(_t("admin_user_not_found", user_id=user_id, role="tester"))


async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Block a user. Usage: /block <user_id> [reason]"""
    if not is_admin_user(str(update.effective_user.id)):
        return

    user_id = _parse_user_id(context.args)
    if not user_id:
        await update.message.reply_text(_t("admin_usage", command="/block <user_id> [reason]"))
        return

    admin_id = str(update.effective_user.id)
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    await add_user_role(user_id, const.ROLE_BLOCKED, admin_id)
    if reason:
        logger.info("User %s blocked by %s. Reason: %s", user_id, admin_id, reason)
    else:
        logger.info("User %s blocked by %s", user_id, admin_id)
    await update.message.reply_text(_t("admin_user_blocked", user_id=user_id))


async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unblock a user. Usage: /unblock <user_id>"""
    if not is_admin_user(str(update.effective_user.id)):
        return

    user_id = _parse_user_id(context.args)
    if not user_id:
        await update.message.reply_text(_t("admin_usage", command="/unblock <user_id>"))
        return

    removed = await remove_user_role(user_id, const.ROLE_BLOCKED)
    if removed:
        await update.message.reply_text(_t("admin_user_unblocked", user_id=user_id))
    else:
        await update.message.reply_text(_t("admin_user_not_found", user_id=user_id, role="blocked"))


async def add_credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add credits to a user. Usage: /add_credits <user_id> <amount>"""
    if not is_admin_user(str(update.effective_user.id)):
        return

    expected_args = 2
    args = context.args or []
    if len(args) < expected_args:
        await update.message.reply_text(
            _t("admin_usage", command="/add_credits <user_id> <amount>")
        )
        return

    user_id = args[0].strip()
    if not user_id.isdigit():
        await update.message.reply_text(
            _t("admin_usage", command="/add_credits <user_id> <amount>")
        )
        return

    try:
        amount = int(args[1])
    except ValueError:
        await update.message.reply_text(
            _t("admin_usage", command="/add_credits <user_id> <amount>")
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            _t("admin_usage", command="/add_credits <user_id> <amount>")
        )
        return

    balance = await admin_add_credits(user_id, amount)
    await update.message.reply_text(
        _t("admin_credits_added", amount=amount, user_id=user_id, balance=balance)
    )
