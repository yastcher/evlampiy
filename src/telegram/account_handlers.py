"""Account hub handlers: balance, stats, WhatsApp linking."""

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.account_linking import generate_link_code, get_linked_whatsapp, unlink
from src.credits import get_total_credits, get_user_tier
from src.dto import UserCredits
from src.localization import translates
from src.mongo import get_chat_language
from src.telegram.chat_params import EventLike, get_chat_id, is_private_chat, reply_text

logger = logging.getLogger(__name__)


async def mystats_command(event: EventLike, bot: Bot) -> None:
    if event.from_user is None:
        return
    user_id = str(event.from_user.id)
    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)

    credits = await get_total_credits(user_id)
    tier = await get_user_tier(user_id)

    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    total_transcriptions = record.total_transcriptions if record else 0
    total_tokens_used = record.total_tokens_used if record else 0
    total_purchased = record.total_credits_purchased if record else 0

    text = (
        translates["mystats_message"]
        .get(language, translates["mystats_message"]["en"])
        .format(
            credits=credits,
            tier=tier.value,
            total_transcriptions=total_transcriptions,
            total_tokens_used=total_tokens_used,
            total_purchased=total_purchased,
        )
    )
    await reply_text(event, text, parse_mode="HTML")


async def link_whatsapp(event: EventLike, bot: Bot) -> None:
    if not is_private_chat(event):
        return
    if event.from_user is None:
        return

    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)
    user_id = str(event.from_user.id)
    code = await generate_link_code(user_id)

    text = (
        translates["whatsapp_link_prompt"]
        .get(language, translates["whatsapp_link_prompt"]["en"])
        .format(code=code)
    )
    await reply_text(event, text)


async def unlink_whatsapp(event: EventLike, bot: Bot) -> None:
    if not is_private_chat(event):
        return
    if event.from_user is None:
        return

    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)
    user_id = str(event.from_user.id)
    result = await unlink(user_id)

    if result:
        await reply_text(
            event,
            translates["whatsapp_unlinked"].get(language, translates["whatsapp_unlinked"]["en"]),
        )
    else:
        await reply_text(
            event,
            translates["whatsapp_not_linked"].get(
                language, translates["whatsapp_not_linked"]["en"]
            ),
        )


async def account_hub(message: Message, bot: Bot) -> None:
    if not is_private_chat(message):
        return
    if message.from_user is None:
        return

    chat_id = get_chat_id(message)
    user_id = str(message.from_user.id)
    language = await get_chat_language(chat_id)

    whatsapp_linked = await get_linked_whatsapp(user_id)

    keyboard: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=translates["btn_buy"][language], callback_data="hub_buy")],
        [
            InlineKeyboardButton(
                text=translates["btn_balance"][language], callback_data="hub_balance",
            )
        ],
        [
            InlineKeyboardButton(
                text=translates["btn_mystats"][language], callback_data="hub_mystats",
            )
        ],
    ]

    if whatsapp_linked:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=translates["btn_unlink_whatsapp"][language],
                    callback_data="hub_unlink_whatsapp",
                )
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=translates["btn_link_whatsapp"][language],
                    callback_data="hub_link_whatsapp",
                )
            ]
        )

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    title = translates["account_hub_title"][language]
    await message.answer(title, reply_markup=reply_markup)
