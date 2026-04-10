"""Settings hub handlers: language, provider, cleanup toggle."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src import const
from src.ai_client import _PROVIDER_LIMITS
from src.config import settings
from src.credits import get_user_tier
from src.dto import UserTier
from src.localization import translates
from src.mongo import (
    get_auto_cleanup,
    get_chat_language,
    get_preferred_provider,
    set_auto_cleanup,
    set_chat_language,
    set_preferred_provider,
)
from src.telegram.chat_params import get_chat_id, is_private_chat, is_user_admin, reply_text

logger = logging.getLogger(__name__)


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    if update.message is None:
        return
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    keyboard = [
        [InlineKeyboardButton("Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton("English", callback_data="set_lang_en")],
        [InlineKeyboardButton("Español", callback_data="set_lang_es")],
        [InlineKeyboardButton("Deutsch", callback_data="set_lang_de")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = translates["choose_language_prompt"].get(
        language, translates["choose_language_prompt"]["en"]
    )
    await update.message.reply_text(prompt, reply_markup=reply_markup)


async def lang_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    query = update.callback_query
    if query is None or query.data is None or query.from_user is None:
        return
    await query.answer()

    lang_code = query.data.split("_")[-1]

    if is_private_chat(update):
        chat_id = f"{const.CHAT_PREFIX_USER}{query.from_user.id}"
    else:
        if query.message is None:
            return
        chat_id = f"{const.CHAT_PREFIX_GROUP}{query.message.chat.id}"

    await query.edit_message_text(text=translates["choose_my_language"][lang_code])
    await set_chat_language(chat_id, lang_code)


async def toggle_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    current = await get_auto_cleanup(chat_id)
    new_value = not current
    await set_auto_cleanup(chat_id, new_value)

    key = "cleanup_enabled" if new_value else "cleanup_disabled"
    text = translates[key].get(language, translates[key]["en"])
    await reply_text(update, text)


async def settings_hub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    if update.message is None:
        return
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    keyboard = [
        [InlineKeyboardButton(translates["btn_language"][language], callback_data="hub_language")],
        [
            InlineKeyboardButton(
                translates["btn_gpt_command"][language], callback_data="hub_gpt_command"
            )
        ],
    ]

    # Show paid-tier options
    if update.effective_user:
        user_id = str(update.effective_user.id)
        tier = await get_user_tier(user_id)
        if tier not in (UserTier.FREE,):
            # Provider selection (when multiple providers available)
            if settings.groq_api_key:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            translates["btn_provider"][language], callback_data="hub_provider"
                        )
                    ]
                )

            # Transcript cleanup toggle
            cleanup_on = await get_auto_cleanup(chat_id)
            cleanup_key = "btn_toggle_cleanup_on" if cleanup_on else "btn_toggle_cleanup_off"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        translates[cleanup_key][language], callback_data="hub_toggle_cleanup"
                    )
                ]
            )

    reply_markup = InlineKeyboardMarkup(keyboard)
    title = translates["settings_hub_title"][language]
    await update.message.reply_text(title, reply_markup=reply_markup)


async def _show_provider_menu(update: Update) -> None:
    query = update.callback_query
    if query is None:
        return
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    current = await get_preferred_provider(chat_id)

    prompt = translates["choose_provider_prompt"].get(
        language, translates["choose_provider_prompt"]["en"]
    )

    check = "\u2705 "
    keyboard = [
        [
            InlineKeyboardButton(
                f"{check if current is None else ''}Auto",
                callback_data="set_prov_auto",
            )
        ],
        [
            InlineKeyboardButton(
                f"{check if current == const.PROVIDER_WIT else ''}Wit.ai",
                callback_data="set_prov_wit",
            )
        ],
    ]
    if settings.groq_api_key:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{check if current == const.PROVIDER_GROQ else ''}Groq",
                    callback_data="set_prov_groq",
                )
            ]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(prompt, reply_markup=reply_markup)


async def hub_show_language_menu(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        return
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    prompt = translates["choose_language_prompt"].get(
        language, translates["choose_language_prompt"]["en"]
    )

    keyboard = [
        [InlineKeyboardButton("Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton("English", callback_data="set_lang_en")],
        [InlineKeyboardButton("Español", callback_data="set_lang_es")],
        [InlineKeyboardButton("Deutsch", callback_data="set_lang_de")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(prompt, reply_markup=reply_markup)


async def hub_show_provider(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_provider_menu(update)


def provider_icon(name: str, keys: dict[str, bool]) -> str:
    """Return check/cross based on whether the provider has a key configured."""
    return "✅" if keys.get(name) else "❌"


def provider_rpm(name: str) -> str:
    rpm = _PROVIDER_LIMITS.get(name)
    return f" {rpm}rpm" if rpm else ""


async def provider_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_user_admin(update, context):
        return

    query = update.callback_query
    if query is None or query.data is None or query.from_user is None:
        return
    await query.answer()

    choice = query.data.replace("set_prov_", "")

    if is_private_chat(update):
        chat_id = f"{const.CHAT_PREFIX_USER}{query.from_user.id}"
    else:
        if query.message is None:
            return
        chat_id = f"{const.CHAT_PREFIX_GROUP}{query.message.chat.id}"

    language = await get_chat_language(chat_id)

    provider_map = {
        "auto": (None, "choose_my_provider_auto"),
        "wit": (const.PROVIDER_WIT, "choose_my_provider_wit"),
        "groq": (const.PROVIDER_GROQ, "choose_my_provider_groq"),
    }

    provider_value, translate_key = provider_map.get(choice, (None, "choose_my_provider_auto"))
    await set_preferred_provider(chat_id, provider_value)
    await query.edit_message_text(
        text=translates[translate_key].get(language, translates[translate_key]["en"])
    )
