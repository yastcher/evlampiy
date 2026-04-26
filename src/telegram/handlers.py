"""Core Telegram handlers: start, GPT command conversation, stats, hub routing."""

import logging
from collections.abc import Sequence

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from src import const
from src.ai_client import CATEGORIZATION_FALLBACK_CHAIN, GPT_FALLBACK_CHAIN
from src.config import settings
from src.credits import current_month_key, get_monthly_stats, is_admin_user
from src.localization import translates
from src.mongo import get_bot_config, get_chat_language, get_gpt_command, set_gpt_command
from src.telegram.account_handlers import (
    link_whatsapp,
    mystats_command,
    unlink_whatsapp,
)
from src.telegram.chat_params import EventLike, get_chat_id, is_user_admin
from src.telegram.obsidian_handlers import (
    categorize_all,
    connect_github,
    disconnect_github,
    setup_obsidian_git,
    toggle_categorize,
    toggle_obsidian,
)
from src.telegram.payments import balance_command, buy_command
from src.telegram.settings_handlers import (
    hub_show_language_menu,
    hub_show_provider,
    provider_icon,
    provider_rpm,
    toggle_cleanup,
)
from src.wit_tracking import get_all_wit_usage_this_month

logger = logging.getLogger(__name__)


class GptCommandStates(StatesGroup):
    """FSM states for the /enter_your_command flow."""

    waiting = State()


# Backwards-compatible alias for tests / older code paths
WAITING_FOR_COMMAND = GptCommandStates.waiting


async def start(message: Message, bot: Bot) -> None:
    if not await is_user_admin(message, bot):
        return

    chat_id = get_chat_id(message)
    chat_language = await get_chat_language(chat_id)
    gpt_command = await get_gpt_command(chat_id)
    text_to_send = translates["start_message"][chat_language].format(
        chat_language=chat_language,
        gpt_command=gpt_command,
    )
    await message.answer(text_to_send, parse_mode="HTML")


async def enter_your_command(message: Message, bot: Bot, state: FSMContext) -> None:
    if not await is_user_admin(message, bot):
        return

    await message.answer("Please enter your command for GPT:")
    await state.set_state(GptCommandStates.waiting)


async def handle_command_input(message: Message, state: FSMContext) -> None:
    text = message.text
    if not text:
        await state.clear()
        return
    chat_id = get_chat_id(message)
    await set_gpt_command(chat_id, text)
    await message.answer(f"Your command '{text}' has been saved.")
    await state.clear()


async def enter_your_command_from_hub(callback: CallbackQuery, state: FSMContext) -> None:
    if not isinstance(callback.message, Message):
        return
    await callback.answer()
    await callback.message.answer("Please enter your command for GPT:")
    await state.set_state(GptCommandStates.waiting)


# ---------------------------------------------------------------------------
# Admin stats
# ---------------------------------------------------------------------------


async def build_stats_text() -> str:
    """Build admin stats message text."""
    month = current_month_key()
    stats = await get_monthly_stats(month)
    wit_limit = settings.wit_free_monthly_limit
    wit_usage_by_lang = await get_all_wit_usage_this_month()

    total_transcriptions = stats.total_transcriptions if stats else 0
    total_payments = stats.total_payments if stats else 0
    total_credits_sold = stats.total_credits_sold if stats else 0
    groq_audio_seconds = stats.groq_audio_seconds if stats else 0

    revenue = total_credits_sold * const.STAR_TO_DOLLAR
    groq_cost = groq_audio_seconds / 3600 * 0.04

    def _wit_status(usage: int) -> str:
        if usage >= wit_limit * 0.95:
            return "CRITICAL"
        if usage >= wit_limit * 0.8:
            return "Warning"
        return "OK"

    keys: dict[str, bool] = {
        const.PROVIDER_GROQ: bool(settings.groq_api_key),
        const.PROVIDER_GEMINI: bool(settings.gemini_api_key),
        const.PROVIDER_ANTHROPIC: bool(settings.anthropic_bot_api_key),
        const.PROVIDER_OPENROUTER: bool(settings.openrouter_api_key),
        const.PROVIDER_OPENAI: bool(settings.gpt_token),
    }

    def _chain_str(primary: str, fallback_chain: Sequence[str]) -> str:
        chain = [primary] + [p for p in fallback_chain if p != primary]
        parts = [f"{p}{provider_rpm(p)} {provider_icon(p, keys)}" for p in chain]
        return " → ".join(parts)

    categ_primary = await get_bot_config(
        "categorization_provider", settings.categorization_provider
    )
    gpt_primary = await get_bot_config("gpt_provider", settings.gpt_provider)
    categ_chain = _chain_str(categ_primary, CATEGORIZATION_FALLBACK_CHAIN)
    gpt_chain = _chain_str(gpt_primary, GPT_FALLBACK_CHAIN)

    all_chain_providers = set(CATEGORIZATION_FALLBACK_CHAIN) | set(GPT_FALLBACK_CHAIN)
    unused_with_key = [p for p, has_key in keys.items() if has_key and p not in all_chain_providers]
    unused_line = f"\n• Not in chain: {', '.join(unused_with_key)}" if unused_with_key else ""

    return (
        f"📊 <b>System Stats ({month})</b>\n\n"
        f"<b>Users</b>\n"
        f"• Total transcriptions: {total_transcriptions:,}\n"
        f"• Payments: {total_payments}\n\n"
        f"<b>Revenue</b>\n"
        f"• Stars received: {total_credits_sold}★\n"
        f"• Credits sold: {total_credits_sold}\n"
        f"• Revenue: ${revenue:.2f}\n\n"
        f"<b>Costs</b>\n"
        f"• Wit.ai / {wit_limit:,} req/mo:\n"
        + "".join(
            f"  - {lang}: {usage:,} ({usage / wit_limit * 100:.1f}%)\n"
            for lang, usage in sorted(wit_usage_by_lang.items())
        )
        + ("  - (no data yet)\n" if not wit_usage_by_lang else "")
        + f"• Groq audio: {groq_audio_seconds} sec/mo (${groq_cost:.2f})"
        f" | limit: {settings.groq_audio_daily_limit:,} sec/day\n\n"
        f"<b>LLM Providers</b>\n"
        f"• Categ: {categ_chain}\n"
        f"• GPT:   {gpt_chain}"
        f"{unused_line}\n\n"
        f"<b>Health</b>\n"
        + "".join(
            f"• Wit.ai ({lang}): "
            f"{'✅' if _wit_status(u) == 'OK' else '⚠️' if _wit_status(u) == 'Warning' else '🚨'} "
            f"{_wit_status(u)}\n"
            for lang, u in sorted(wit_usage_by_lang.items())
        )
        + ("• Wit.ai: ✅ OK (no data)\n" if not wit_usage_by_lang else "")
        + f"• Groq: {'✅' if settings.groq_api_key else '❌'} "
        f"{'Configured' if settings.groq_api_key else 'Not configured'}"
    )


async def stats_command(message: Message) -> None:
    if message.from_user is None:
        return
    if not is_admin_user(str(message.from_user.id)):
        return
    text = await build_stats_text()
    await message.answer(text, parse_mode="HTML")


# ---------------------------------------------------------------------------
# Hub callback router — dispatches hub_* callbacks to the correct handler
# ---------------------------------------------------------------------------

_HUB_ACTIONS = {
    "language": hub_show_language_menu,
    "buy": buy_command,
    "balance": balance_command,
    "mystats": mystats_command,
    "toggle_obsidian": toggle_obsidian,
    "toggle_categorize": toggle_categorize,
    "toggle_cleanup": toggle_cleanup,
    "categorize": categorize_all,
    "setup_obsidian_git": setup_obsidian_git,
    "connect_github": connect_github,
    "disconnect_github": disconnect_github,
    "link_whatsapp": link_whatsapp,
    "unlink_whatsapp": unlink_whatsapp,
    "provider": hub_show_provider,
}


async def hub_callback_router(callback: CallbackQuery, bot: Bot) -> None:
    if callback.data is None:
        return
    await callback.answer()

    action = callback.data.replace("hub_", "")
    handler = _HUB_ACTIONS.get(action)
    if handler:
        # All hub-action handlers accept (event, bot) where event is Message or CallbackQuery
        event: EventLike = callback
        await handler(event, bot)
