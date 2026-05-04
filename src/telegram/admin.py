"""Admin Telegram handlers for managing VIP/tester/blocked users."""

import logging
import typing
from collections.abc import Sequence

from aiogram.filters import CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src import const
from src.config import settings
from src.credits import admin_add_credits, is_admin_user
from src.localization import translates
from src.mongo import (
    add_user_role,
    get_bot_config,
    get_users_by_role,
    remove_user_role,
    set_bot_config,
)
from src.services.stats_service import build_stats_text

logger = logging.getLogger(__name__)

ADMIN_LANG = "en"

_LLM_PROVIDERS = [const.PROVIDER_OPENROUTER, const.PROVIDER_GEMINI, const.PROVIDER_GROQ]


def _t(key: str, **kwargs: typing.Any) -> str:
    """Get admin translation (always English for admin interface)."""
    text = translates[key].get(ADMIN_LANG, translates[key]["en"])
    if kwargs:
        return text.format(**kwargs)
    return text


def _hub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_t("btn_manage_vip"), callback_data="adm_vip")],
            [InlineKeyboardButton(text=_t("btn_manage_testers"), callback_data="adm_testers")],
            [InlineKeyboardButton(text=_t("btn_manage_blocked"), callback_data="adm_blocked")],
            [InlineKeyboardButton(text=_t("btn_admin_stats"), callback_data="adm_stats")],
            [InlineKeyboardButton(text=_t("btn_add_credits"), callback_data="adm_credits")],
            [InlineKeyboardButton(text="🤖 LLM Providers", callback_data="adm_providers")],
        ]
    )


async def _build_providers_panel() -> tuple[str, InlineKeyboardMarkup]:
    categ = await get_bot_config("categorization_provider", settings.categorization_provider)
    gpt = await get_bot_config("gpt_provider", settings.gpt_provider)

    text = (
        f"🤖 <b>LLM Providers</b>\n\n"
        f"• Categ: <code>{categ}</code>\n"
        f"• GPT:   <code>{gpt}</code>\n\n"
        f"Select to change:"
    )

    def _btn(prefix: str, current: str, p: str) -> InlineKeyboardButton:
        label = f"✓ {p}" if p == current else p
        return InlineKeyboardButton(text=label, callback_data=f"adm_prov_{prefix}_{p}")

    keyboard = [
        [_btn("c", categ, p) for p in _LLM_PROVIDERS],
        [_btn("g", gpt, p) for p in _LLM_PROVIDERS],
        [InlineKeyboardButton(text="← Back", callback_data="adm_back")],
    ]
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard)


def _split_args(command: CommandObject | typing.Any | None) -> list[str]:
    """Extract positional args from a CommandObject. Tolerates a pre-split list."""
    if command is None:
        return []
    raw = getattr(command, "args", None)
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(a) for a in raw]
    return str(raw).split()


def _parse_user_id(args: Sequence[str]) -> str | None:
    """Extract and validate user_id from command arguments."""
    if not args:
        return None
    user_id = args[0].strip()
    if not user_id.isdigit():
        return None
    return user_id


async def admin_hub(message: Message) -> None:
    """Admin panel with inline keyboard."""
    if message.from_user is None:
        return
    if not is_admin_user(str(message.from_user.id)):
        return
    await message.answer(_t("admin_hub_title"), reply_markup=_hub_keyboard())


async def _handle_role_list(callback: CallbackQuery, role: str, text_key: str) -> None:
    if not isinstance(callback.message, Message):
        return
    users = await get_users_by_role(role)
    user_list = "\n".join(f"• {uid}" for uid in users) if users else _t("admin_list_empty")
    await callback.message.edit_text(_t(text_key, users=user_list), parse_mode="HTML")


async def _handle_stats(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    text = await build_stats_text()
    await callback.message.edit_text(text, parse_mode="HTML")


async def _handle_credits(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    text = _t("admin_usage", command="/add_credits <user_id> <amount>")
    await callback.message.edit_text(text)


async def _handle_providers(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    text, markup = await _build_providers_panel()
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


async def _handle_back(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(_t("admin_hub_title"), reply_markup=_hub_keyboard())


async def _handle_provider_change(callback: CallbackQuery, action: str) -> None:
    """Handle prov_c_* / prov_g_* callback actions."""
    config_key = "categorization_provider" if action[5] == "c" else "gpt_provider"
    provider = action[7:]
    if provider in _LLM_PROVIDERS:
        await set_bot_config(config_key, provider)
    await _handle_providers(callback)


_ACTION_HANDLERS: dict[str, typing.Callable[[CallbackQuery], typing.Awaitable[None]]] = {
    "vip": lambda q: _handle_role_list(q, const.ROLE_VIP, "admin_vip_list"),
    "testers": lambda q: _handle_role_list(q, const.ROLE_TESTER, "admin_tester_list"),
    "blocked": lambda q: _handle_role_list(q, const.ROLE_BLOCKED, "admin_blocked_list"),
    "stats": _handle_stats,
    "credits": _handle_credits,
    "providers": _handle_providers,
    "back": _handle_back,
}


async def admin_callback_router(callback: CallbackQuery) -> None:
    """Route admin hub button presses."""
    if callback.from_user is None or callback.data is None:
        return
    if not is_admin_user(str(callback.from_user.id)):
        return
    await callback.answer()

    action = callback.data.replace("adm_", "")

    _MIN_PROV_ACTION_LEN = 7  # "prov_c_" prefix
    if action.startswith("prov_") and len(action) >= _MIN_PROV_ACTION_LEN:
        await _handle_provider_change(callback, action)
        return

    handler = _ACTION_HANDLERS.get(action)
    if handler:
        await handler(callback)


async def add_vip_command(message: Message, command: CommandObject) -> None:
    """Add a user to VIP list. Usage: /add_vip <user_id>"""
    if message.from_user is None or not is_admin_user(str(message.from_user.id)):
        return

    user_id = _parse_user_id(_split_args(command))
    if not user_id:
        await message.answer(_t("admin_usage", command="/add_vip <user_id>"))
        return

    admin_id = str(message.from_user.id)
    await add_user_role(user_id, const.ROLE_VIP, admin_id)
    await message.answer(_t("admin_user_added", user_id=user_id, role="VIP"))


async def remove_vip_command(message: Message, command: CommandObject) -> None:
    """Remove a user from VIP list. Usage: /remove_vip <user_id>"""
    if message.from_user is None or not is_admin_user(str(message.from_user.id)):
        return

    user_id = _parse_user_id(_split_args(command))
    if not user_id:
        await message.answer(_t("admin_usage", command="/remove_vip <user_id>"))
        return

    removed = await remove_user_role(user_id, const.ROLE_VIP)
    if removed:
        await message.answer(_t("admin_user_removed", user_id=user_id, role="VIP"))
    else:
        await message.answer(_t("admin_user_not_found", user_id=user_id, role="VIP"))


async def add_tester_command(message: Message, command: CommandObject) -> None:
    """Add a user to tester list. Usage: /add_tester <user_id>"""
    if message.from_user is None or not is_admin_user(str(message.from_user.id)):
        return

    user_id = _parse_user_id(_split_args(command))
    if not user_id:
        await message.answer(_t("admin_usage", command="/add_tester <user_id>"))
        return

    admin_id = str(message.from_user.id)
    await add_user_role(user_id, const.ROLE_TESTER, admin_id)
    await message.answer(_t("admin_user_added", user_id=user_id, role="tester"))


async def remove_tester_command(message: Message, command: CommandObject) -> None:
    """Remove a user from tester list. Usage: /remove_tester <user_id>"""
    if message.from_user is None or not is_admin_user(str(message.from_user.id)):
        return

    user_id = _parse_user_id(_split_args(command))
    if not user_id:
        await message.answer(_t("admin_usage", command="/remove_tester <user_id>"))
        return

    removed = await remove_user_role(user_id, const.ROLE_TESTER)
    if removed:
        await message.answer(_t("admin_user_removed", user_id=user_id, role="tester"))
    else:
        await message.answer(_t("admin_user_not_found", user_id=user_id, role="tester"))


async def block_command(message: Message, command: CommandObject) -> None:
    """Block a user. Usage: /block <user_id> [reason]"""
    if message.from_user is None or not is_admin_user(str(message.from_user.id)):
        return

    args = _split_args(command)
    user_id = _parse_user_id(args)
    if not user_id:
        await message.answer(_t("admin_usage", command="/block <user_id> [reason]"))
        return

    admin_id = str(message.from_user.id)
    reason = " ".join(args[1:]) if len(args) > 1 else ""
    await add_user_role(user_id, const.ROLE_BLOCKED, admin_id)
    if reason:
        logger.info("User %s blocked by %s. Reason: %s", user_id, admin_id, reason)
    else:
        logger.info("User %s blocked by %s", user_id, admin_id)
    await message.answer(_t("admin_user_blocked", user_id=user_id))


async def unblock_command(message: Message, command: CommandObject) -> None:
    """Unblock a user. Usage: /unblock <user_id>"""
    if message.from_user is None or not is_admin_user(str(message.from_user.id)):
        return

    user_id = _parse_user_id(_split_args(command))
    if not user_id:
        await message.answer(_t("admin_usage", command="/unblock <user_id>"))
        return

    removed = await remove_user_role(user_id, const.ROLE_BLOCKED)
    if removed:
        await message.answer(_t("admin_user_unblocked", user_id=user_id))
    else:
        await message.answer(_t("admin_user_not_found", user_id=user_id, role="blocked"))


async def add_credits_command(message: Message, command: CommandObject) -> None:
    """Add credits to a user. Usage: /add_credits <user_id> <amount>"""
    if message.from_user is None or not is_admin_user(str(message.from_user.id)):
        return

    expected_args = 2
    args = _split_args(command)
    usage_text = _t("admin_usage", command="/add_credits <user_id> <amount>")
    if len(args) < expected_args:
        await message.answer(usage_text)
        return

    user_id = args[0].strip()
    if not user_id.isdigit():
        await message.answer(usage_text)
        return

    try:
        amount = int(args[1])
    except ValueError:
        await message.answer(usage_text)
        return

    if amount <= 0:
        await message.answer(usage_text)
        return

    balance = await admin_add_credits(user_id, amount)
    await message.answer(_t("admin_credits_added", amount=amount, user_id=user_id, balance=balance))
