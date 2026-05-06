"""Settings hub handlers: language, provider, cleanup toggle."""

import logging

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

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
    set_chat_language,
)
from src.services.settings_service import set_chat_provider_choice, toggle_auto_cleanup
from src.telegram.chat_params import (
    EventLike,
    get_chat_id,
    is_private_chat,
    is_user_admin,
    reply_text,
)

logger = logging.getLogger(__name__)


def _build_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Русский", callback_data="set_lang_ru")],
            [InlineKeyboardButton(text="English", callback_data="set_lang_en")],
            [InlineKeyboardButton(text="Español", callback_data="set_lang_es")],
            [InlineKeyboardButton(text="Deutsch", callback_data="set_lang_de")],
        ]
    )


async def choose_language(message: Message, bot: Bot) -> None:
    if not await is_user_admin(message, bot):
        return

    chat_id = get_chat_id(message)
    language = await get_chat_language(chat_id)
    prompt = translates["choose_language_prompt"].get(
        language, translates["choose_language_prompt"]["en"]
    )
    await message.answer(prompt, reply_markup=_build_language_keyboard())


async def lang_buttons(callback: CallbackQuery, bot: Bot) -> None:
    if not await is_user_admin(callback, bot):
        return
    if callback.data is None or callback.from_user is None:
        return
    await callback.answer()

    lang_code = callback.data.split("_")[-1]

    if is_private_chat(callback):
        chat_id = f"{const.CHAT_PREFIX_USER}{callback.from_user.id}"
    else:
        if not isinstance(callback.message, Message):
            return
        chat_id = f"{const.CHAT_PREFIX_GROUP}{callback.message.chat.id}"

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text=translates["choose_my_language"][lang_code])
    await set_chat_language(chat_id, lang_code)


async def toggle_cleanup(event: EventLike, bot: Bot) -> None:
    if not await is_user_admin(event, bot):
        return

    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)
    new_value = await toggle_auto_cleanup(chat_id)

    key = "cleanup_enabled" if new_value else "cleanup_disabled"
    text = translates[key].get(language, translates[key]["en"])
    await reply_text(event, text)


async def settings_hub(message: Message, bot: Bot) -> None:
    if not await is_user_admin(message, bot):
        return

    chat_id = get_chat_id(message)
    language = await get_chat_language(chat_id)

    keyboard: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=translates["btn_language"][language], callback_data="hub_language"
            )
        ],
        [
            InlineKeyboardButton(
                text=translates["btn_gpt_command"][language], callback_data="hub_gpt_command"
            )
        ],
    ]

    if message.from_user is not None:
        user_id = str(message.from_user.id)
        tier = await get_user_tier(user_id)
        if tier not in (UserTier.FREE,):
            if settings.groq_api_key:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text=translates["btn_provider"][language],
                            callback_data="hub_provider",
                        )
                    ]
                )

            cleanup_on = await get_auto_cleanup(chat_id)
            cleanup_key = "btn_toggle_cleanup_on" if cleanup_on else "btn_toggle_cleanup_off"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=translates[cleanup_key][language],
                        callback_data="hub_toggle_cleanup",
                    )
                ]
            )

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    title = translates["settings_hub_title"][language]
    await message.answer(title, reply_markup=reply_markup)


async def _show_provider_menu(callback: CallbackQuery) -> None:
    if not isinstance(callback.message, Message):
        return
    chat_id = get_chat_id(callback)
    language = await get_chat_language(chat_id)
    current = await get_preferred_provider(chat_id)

    prompt = translates["choose_provider_prompt"].get(
        language, translates["choose_provider_prompt"]["en"]
    )

    check = "✅ "
    keyboard: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"{check if current is None else ''}Auto",
                callback_data="set_prov_auto",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{check if current == const.PROVIDER_WIT else ''}Wit.ai",
                callback_data="set_prov_wit",
            )
        ],
    ]
    if settings.groq_api_key:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{check if current == const.PROVIDER_GROQ else ''}Groq",
                    callback_data="set_prov_groq",
                )
            ]
        )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await callback.message.edit_text(prompt, reply_markup=reply_markup)


async def hub_show_language_menu(event: EventLike, bot: Bot) -> None:
    if not isinstance(event, CallbackQuery):
        return
    if not isinstance(event.message, Message):
        return
    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)
    prompt = translates["choose_language_prompt"].get(
        language, translates["choose_language_prompt"]["en"]
    )
    await event.message.edit_text(prompt, reply_markup=_build_language_keyboard())


async def hub_show_provider(event: EventLike, bot: Bot) -> None:
    if isinstance(event, CallbackQuery):
        await _show_provider_menu(event)


def provider_icon(name: str, keys: dict[str, bool]) -> str:
    """Return check/cross based on whether the provider has a key configured."""
    return "✅" if keys.get(name) else "❌"


def provider_rpm(name: str) -> str:
    rpm = _PROVIDER_LIMITS.get(name)
    return f" {rpm}rpm" if rpm else ""


async def provider_buttons(callback: CallbackQuery, bot: Bot) -> None:
    if not await is_user_admin(callback, bot):
        return
    if callback.data is None or callback.from_user is None:
        return
    await callback.answer()

    choice = callback.data.replace("set_prov_", "")

    if is_private_chat(callback):
        chat_id = f"{const.CHAT_PREFIX_USER}{callback.from_user.id}"
    else:
        if not isinstance(callback.message, Message):
            return
        chat_id = f"{const.CHAT_PREFIX_GROUP}{callback.message.chat.id}"

    language = await get_chat_language(chat_id)
    translate_key = await set_chat_provider_choice(chat_id, choice)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text=translates[translate_key].get(language, translates[translate_key]["en"])
        )
