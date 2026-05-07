"""Core Telegram handlers: start, GPT command conversation, stats, hub routing."""

import logging

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from src.credits import is_admin_user
from src.localization import translates
from src.mongo import get_chat_language, get_gpt_command, set_gpt_command
from src.services.stats_service import build_stats_text
from src.telegram.chat_params import EventLike, get_chat_id, is_user_admin
from src.telegram.handlers.account import (
    link_whatsapp,
    mystats_command,
    unlink_whatsapp,
)
from src.telegram.handlers.obsidian import (
    categorize_all,
    connect_github,
    disconnect_github,
    setup_obsidian_git,
    toggle_categorize,
    toggle_obsidian,
)
from src.telegram.handlers.payments import balance_command, buy_command
from src.telegram.handlers.settings import (
    hub_show_language_menu,
    hub_show_provider,
    toggle_cleanup,
)

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
