"""Obsidian / GitHub integration handlers for Telegram bot."""

import asyncio
import dataclasses
import logging
import re

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src import obsidian_layout
from src.github_api import (
    create_obsidian_git_config,
    get_or_create_obsidian_repo,
    list_user_repos,
)
from src.github_oauth import get_github_device_code, poll_github_for_token
from src.localization import translates
from src.mongo import (
    clear_github_settings,
    get_auto_categorize,
    get_chat_language,
    get_github_settings,
    get_save_to_obsidian,
    set_github_settings,
    set_save_to_obsidian,
)
from src.services.notes_service import (
    categorize_all_for_chat,
    toggle_auto_categorize,
    toggle_save_to_obsidian,
)
from src.telegram.chat_params import EventLike, get_chat_id, is_user_admin, reply_text
from src.types import ChatId

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task[None]] = set()

# Callback prefix for repo-selection buttons; `REPO_PICK_NEW` (a member) opens the
# "create new repo" text-input flow. Registered in `telegram/setup.py`.
REPO_PICK_PREFIX = "ghrepo_"
REPO_PICK_NEW = "ghrepo_new"

# GitHub repo name rules: letters, digits, `.`, `-`, `_`, up to 100 chars.
_REPO_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class GithubRepoStates(StatesGroup):
    """FSM states for the connect flow's 'create new repo' text input."""

    waiting_for_name = State()


@dataclasses.dataclass(slots=True)
class _PendingConnect:
    """A GitHub token awaiting the user's repo choice, held only in memory."""

    token: str
    repos: list[str]


class _PendingConnectStore:
    """Per-chat transient store bridging OAuth completion and the repo pick.

    The token arrives in a background poll task, but the repo is chosen in a later
    callback / text message — so it is parked here (never logged, never persisted
    until a repo is confirmed). Lost on process restart → user re-runs /connect_github.
    """

    def __init__(self) -> None:
        self._items: dict[ChatId, _PendingConnect] = {}

    def put(self, chat_id: ChatId, token: str, repos: list[str]) -> None:
        self._items[chat_id] = _PendingConnect(token=token, repos=list(repos))

    def get(self, chat_id: ChatId) -> _PendingConnect | None:
        return self._items.get(chat_id)

    def pop(self, chat_id: ChatId) -> _PendingConnect | None:
        return self._items.pop(chat_id, None)

    def clear(self) -> None:
        self._items.clear()


_pending_connects = _PendingConnectStore()


def _resolve_chat_id_int(event: EventLike) -> int | None:
    if isinstance(event, Message):
        return event.chat.id
    if event.message is not None:
        return event.message.chat.id
    return None


async def connect_github(event: EventLike, bot: Bot) -> None:
    if not await is_user_admin(event, bot):
        return

    effective_chat_id = _resolve_chat_id_int(event)
    if effective_chat_id is None:
        return

    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)

    device_info = await get_github_device_code()
    if "error" in device_info:
        text = translates["github_auth_failed"].get(language, translates["github_auth_failed"]["en"])
        await reply_text(event, text)
        logger.error("GitHub device code error: %s", device_info)
        return

    verification_uri = device_info["verification_uri"]
    user_code = device_info["user_code"]
    expires_in = device_info["expires_in"]
    interval = device_info["interval"]

    text = (
        translates["github_auth_prompt"]
        .get(language, translates["github_auth_prompt"]["en"])
        .format(
            verification_uri=verification_uri,
            user_code=user_code,
            expires_in=expires_in,
        )
    )
    await reply_text(event, text)

    async def _poll_and_offer() -> None:
        token = await poll_github_for_token(
            device_code=str(device_info["device_code"]),
            interval=int(interval),
            expires_in=int(expires_in),
        )
        if not token:
            text = translates["github_auth_timeout"].get(language, translates["github_auth_timeout"]["en"])
            await bot.send_message(chat_id=effective_chat_id, text=text)
            return

        repos = await list_user_repos(token)
        _pending_connects.put(chat_id, token, repos)

        prompt = translates["github_choose_repo"].get(language, translates["github_choose_repo"]["en"])
        await bot.send_message(
            chat_id=effective_chat_id,
            text=prompt,
            reply_markup=_build_repo_keyboard(repos, language),
        )

    task = asyncio.create_task(_poll_and_offer())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def _build_repo_keyboard(repos: list[str], language: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"{REPO_PICK_PREFIX}{index}")]
        for index, name in enumerate(repos)
    ]
    create_label = translates["btn_create_new_repo"].get(language, translates["btn_create_new_repo"]["en"])
    rows.append([InlineKeyboardButton(text=create_label, callback_data=REPO_PICK_NEW)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _parse_repo_index(data: str | None) -> int | None:
    if data is None:
        return None
    raw = data.removeprefix(REPO_PICK_PREFIX)
    return int(raw) if raw.isdigit() else None


async def _finalize_connect(
    bot: Bot, effective_chat_id: int, chat_id: ChatId, token: str, repo_name: str, language: str
) -> None:
    """Create-or-reuse the chosen repo, persist settings, and confirm to the user."""
    repo_info = await get_or_create_obsidian_repo(token, repo_name)
    if not repo_info:
        text = translates["github_repo_failed"].get(language, translates["github_repo_failed"]["en"])
        await bot.send_message(chat_id=effective_chat_id, text=text)
        return

    await set_github_settings(chat_id, repo_info.owner, repo_info.repo, repo_info.token)
    await set_save_to_obsidian(chat_id, True)

    text = (
        translates["github_connected"]
        .get(language, translates["github_connected"]["en"])
        .format(owner=repo_info.owner, repo=repo_info.repo)
    )
    await bot.send_message(chat_id=effective_chat_id, text=text)


async def pick_repo_callback(callback: CallbackQuery, bot: Bot, state: FSMContext) -> None:
    """Handle a repo-selection button: connect to the picked repo or ask for a new name."""
    if not isinstance(callback.message, Message):
        return
    if not await is_user_admin(callback, bot):
        return
    await callback.answer()

    chat_id = get_chat_id(callback)
    language = await get_chat_language(chat_id)
    pending = _pending_connects.get(chat_id)
    if pending is None:
        await callback.message.answer(
            translates["github_session_expired"].get(language, translates["github_session_expired"]["en"])
        )
        return

    if callback.data == REPO_PICK_NEW:
        await state.set_state(GithubRepoStates.waiting_for_name)
        await callback.message.answer(
            translates["github_enter_repo_name"].get(language, translates["github_enter_repo_name"]["en"])
        )
        return

    index = _parse_repo_index(callback.data)
    if index is None or index >= len(pending.repos):
        await callback.message.answer(
            translates["github_session_expired"].get(language, translates["github_session_expired"]["en"])
        )
        return

    _pending_connects.pop(chat_id)
    await _finalize_connect(bot, callback.message.chat.id, chat_id, pending.token, pending.repos[index], language)


async def handle_repo_name_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Create a new repo from the name typed by the user during the connect flow."""
    if not await is_user_admin(message, bot):
        return
    chat_id = get_chat_id(message)
    language = await get_chat_language(chat_id)
    pending = _pending_connects.get(chat_id)
    if pending is None:
        await state.clear()
        await message.answer(
            translates["github_session_expired"].get(language, translates["github_session_expired"]["en"])
        )
        return

    name = (message.text or "").strip()
    if not _REPO_NAME_RE.match(name):
        # Stay in the state so the user can retry with a valid name.
        await message.answer(
            translates["github_repo_name_invalid"].get(language, translates["github_repo_name_invalid"]["en"])
        )
        return

    _pending_connects.pop(chat_id)
    await state.clear()
    await _finalize_connect(bot, message.chat.id, chat_id, pending.token, name, language)


async def toggle_obsidian(event: EventLike, bot: Bot) -> None:
    if not await is_user_admin(event, bot):
        return

    chat_id = get_chat_id(event)
    new_value = await toggle_save_to_obsidian(chat_id)

    language = await get_chat_language(chat_id)
    key = "obsidian_sync_enabled" if new_value else "obsidian_sync_disabled"
    await reply_text(event, translates[key].get(language, translates[key]["en"]))


async def disconnect_github(event: EventLike, bot: Bot) -> None:
    if not await is_user_admin(event, bot):
        return

    chat_id = get_chat_id(event)
    await clear_github_settings(chat_id)
    language = await get_chat_language(chat_id)
    await reply_text(
        event,
        translates["github_disconnected"].get(language, translates["github_disconnected"]["en"]),
    )


async def toggle_categorize(event: EventLike, bot: Bot) -> None:
    if not await is_user_admin(event, bot):
        return

    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)
    new_value = await toggle_auto_categorize(chat_id)

    key = "categorize_enabled" if new_value else "categorize_disabled"
    text = translates[key].get(language, translates[key]["en"])
    await reply_text(event, text)


async def categorize_all(event: EventLike, bot: Bot) -> None:
    if not await is_user_admin(event, bot):
        return

    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)
    has_repo, count = await categorize_all_for_chat(chat_id)

    if not has_repo:
        text = translates["github_not_connected"].get(language, translates["github_not_connected"]["en"])
        await reply_text(event, text)
        return

    if count > 0:
        text = translates["categorize_done"].get(language, translates["categorize_done"]["en"])
        await reply_text(event, text.format(count=count))
    else:
        text = translates["categorize_no_files"].get(language, translates["categorize_no_files"]["en"])
        await reply_text(event, text)


async def obsidian_hub(message: Message, bot: Bot) -> None:
    if not await is_user_admin(message, bot):
        return

    chat_id = get_chat_id(message)
    language = await get_chat_language(chat_id)
    repo_info = await get_github_settings(chat_id)

    keyboard: list[list[InlineKeyboardButton]]
    if not repo_info:
        keyboard = [
            [
                InlineKeyboardButton(
                    text=translates["btn_connect_github"][language],
                    callback_data="hub_connect_github",
                )
            ],
        ]
    else:
        sync_on = await get_save_to_obsidian(chat_id)
        sort_on = await get_auto_categorize(chat_id)

        sync_label = translates["btn_toggle_sync_on" if sync_on else "btn_toggle_sync_off"][language]
        sort_label = translates["btn_toggle_sort_on" if sort_on else "btn_toggle_sort_off"][language]

        keyboard = [
            [InlineKeyboardButton(text=sync_label, callback_data="hub_toggle_obsidian")],
            [InlineKeyboardButton(text=sort_label, callback_data="hub_toggle_categorize")],
            [
                InlineKeyboardButton(
                    text=translates["btn_categorize_all"][language],
                    callback_data="hub_categorize",
                )
            ],
            [
                InlineKeyboardButton(
                    text=translates["btn_setup_obsidian_git"][language],
                    callback_data="hub_setup_obsidian_git",
                )
            ],
            [
                InlineKeyboardButton(
                    text=translates["btn_disconnect_github"][language],
                    callback_data="hub_disconnect_github",
                )
            ],
        ]

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    if repo_info:
        title = translates["obsidian_hub_connected"][language].format(
            owner=repo_info.owner, repo=repo_info.repo, inbox_dir=obsidian_layout.inbox_dir()
        )
    else:
        title = translates["obsidian_hub_title"][language]
    await message.answer(title, reply_markup=reply_markup, parse_mode="HTML")


async def setup_obsidian_git(event: EventLike, bot: Bot) -> None:
    if not isinstance(event, CallbackQuery):
        return
    if not isinstance(event.message, Message):
        return
    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)
    repo_info = await get_github_settings(chat_id)
    if not repo_info:
        await event.message.edit_text(translates["github_not_connected"][language])
        return
    success = await create_obsidian_git_config(repo_info)
    key = "obsidian_git_setup_done" if success else "obsidian_git_setup_failed"
    await event.answer(translates[key][language], show_alert=True)
