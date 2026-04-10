"""Obsidian / GitHub integration handlers for Telegram bot."""

import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.categorization import categorize_all_income
from src.github_api import create_obsidian_git_config, get_or_create_obsidian_repo
from src.github_oauth import get_github_device_code, poll_github_for_token
from src.localization import translates
from src.mongo import (
    clear_github_settings,
    get_auto_categorize,
    get_chat_language,
    get_github_settings,
    get_save_to_obsidian,
    set_auto_categorize,
    set_github_settings,
    set_save_to_obsidian,
)
from src.telegram.chat_params import get_chat_id, is_user_admin, reply_text

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task[None]] = set()


async def connect_github(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    if update.effective_chat is None:
        return
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    device_info = await get_github_device_code()
    if "error" in device_info:
        text = translates["github_auth_failed"].get(
            language, translates["github_auth_failed"]["en"]
        )
        await reply_text(update, text)
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
    await reply_text(update, text)

    effective_chat_id = update.effective_chat.id

    async def _poll_and_setup() -> None:
        token = await poll_github_for_token(
            device_code=str(device_info["device_code"]),
            interval=int(interval),
            expires_in=int(expires_in),
        )
        if not token:
            text = translates["github_auth_timeout"].get(
                language, translates["github_auth_timeout"]["en"]
            )
            await context.bot.send_message(
                chat_id=effective_chat_id,
                text=text,
            )
            return

        repo_info = await get_or_create_obsidian_repo(token)
        if not repo_info:
            text = translates["github_repo_failed"].get(
                language, translates["github_repo_failed"]["en"]
            )
            await context.bot.send_message(
                chat_id=effective_chat_id,
                text=text,
            )
            return

        await set_github_settings(chat_id, repo_info.owner, repo_info.repo, repo_info.token)
        await set_save_to_obsidian(chat_id, True)

        text = (
            translates["github_connected"]
            .get(language, translates["github_connected"]["en"])
            .format(
                owner=repo_info.owner,
                repo=repo_info.repo,
            )
        )
        await context.bot.send_message(
            chat_id=effective_chat_id,
            text=text,
        )

    task = asyncio.create_task(_poll_and_setup())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def toggle_obsidian(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    current = await get_save_to_obsidian(chat_id)
    new_value = not current
    await set_save_to_obsidian(chat_id, new_value)

    language = await get_chat_language(chat_id)
    key = "obsidian_sync_enabled" if new_value else "obsidian_sync_disabled"
    await reply_text(update, translates[key].get(language, translates[key]["en"]))


async def disconnect_github(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    await clear_github_settings(chat_id)
    language = await get_chat_language(chat_id)
    await reply_text(
        update,
        translates["github_disconnected"].get(language, translates["github_disconnected"]["en"]),
    )


async def toggle_categorize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    current = await get_auto_categorize(chat_id)
    new_value = not current
    await set_auto_categorize(chat_id, new_value)

    key = "categorize_enabled" if new_value else "categorize_disabled"
    text = translates[key].get(language, translates[key]["en"])
    await reply_text(update, text)


async def categorize_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    repo_info = await get_github_settings(chat_id)

    if not repo_info:
        text = translates["github_not_connected"].get(
            language, translates["github_not_connected"]["en"]
        )
        await reply_text(update, text)
        return

    count = await categorize_all_income(repo_info)

    if count > 0:
        text = translates["categorize_done"].get(language, translates["categorize_done"]["en"])
        await reply_text(update, text.format(count=count))
    else:
        text = translates["categorize_no_files"].get(
            language, translates["categorize_no_files"]["en"]
        )
        await reply_text(update, text)


async def obsidian_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    if update.message is None:
        return
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    repo_info = await get_github_settings(chat_id)

    if not repo_info:
        keyboard = [
            [
                InlineKeyboardButton(
                    translates["btn_connect_github"][language], callback_data="hub_connect_github"
                )
            ],
        ]
    else:
        sync_on = await get_save_to_obsidian(chat_id)
        sort_on = await get_auto_categorize(chat_id)

        sync_label = translates["btn_toggle_sync_on" if sync_on else "btn_toggle_sync_off"][
            language
        ]
        sort_label = translates["btn_toggle_sort_on" if sort_on else "btn_toggle_sort_off"][
            language
        ]

        keyboard = [
            [InlineKeyboardButton(sync_label, callback_data="hub_toggle_obsidian")],
            [InlineKeyboardButton(sort_label, callback_data="hub_toggle_categorize")],
            [
                InlineKeyboardButton(
                    translates["btn_categorize_all"][language], callback_data="hub_categorize"
                )
            ],
            [
                InlineKeyboardButton(
                    translates["btn_setup_obsidian_git"][language],
                    callback_data="hub_setup_obsidian_git",
                )
            ],
            [
                InlineKeyboardButton(
                    translates["btn_disconnect_github"][language],
                    callback_data="hub_disconnect_github",
                )
            ],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if repo_info:
        title = translates["obsidian_hub_connected"][language].format(
            owner=repo_info.owner,
            repo=repo_info.repo,
        )
    else:
        title = translates["obsidian_hub_title"][language]
    await update.message.reply_text(title, reply_markup=reply_markup, parse_mode="HTML")


async def setup_obsidian_git(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    repo_info = await get_github_settings(chat_id)
    if not repo_info:
        await query.edit_message_text(translates["github_not_connected"][language])
        return
    success = await create_obsidian_git_config(repo_info)
    key = "obsidian_git_setup_done" if success else "obsidian_git_setup_failed"
    await query.answer(translates[key][language], show_alert=True)
