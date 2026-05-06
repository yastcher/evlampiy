"""Telegram Stars payment handlers."""

import logging

from aiogram import Bot
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from src import const
from src.alerts import check_and_send_alerts
from src.config import settings
from src.credits import current_month_key, get_credits
from src.dto import UserMonthlyUsage
from src.localization import translates
from src.mongo import get_chat_language
from src.services.payments_service import CREDIT_PACKAGES, award_tokens, package_payload
from src.telegram.chat_params import EventLike, get_chat_id, reply_text

logger = logging.getLogger(__name__)


def _format_duration(seconds: int) -> str:
    """Format seconds as 'Xm Ys'."""
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


async def buy_command(event: EventLike, bot: Bot) -> None:
    """Show credit packages for purchase."""
    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)

    keyboard: list[list[InlineKeyboardButton]] = []
    for idx, pkg in enumerate(CREDIT_PACKAGES):
        label = f"{pkg['name']} — {pkg['tokens']} tokens ({pkg['stars']}★)"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"buy_pkg_{idx}")])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    text = translates["buy_packages_prompt"].get(language, translates["buy_packages_prompt"]["en"])
    await reply_text(event, text, reply_markup=reply_markup)


async def buy_package_callback(callback: CallbackQuery, bot: Bot) -> None:
    """Handle package selection and send invoice."""
    if callback.data is None:
        return
    await callback.answer()

    idx = int(callback.data.split("_")[-1])
    pkg = CREDIT_PACKAGES[idx]

    if not isinstance(callback.message, Message):
        return
    chat_id = callback.message.chat.id
    await bot.send_invoice(
        chat_id=chat_id,
        title=f"{pkg['name']} Token Package",
        description=f"{pkg['tokens']} tokens for voice transcription",
        payload=package_payload(idx),
        currency=const.TELEGRAM_STARS_CURRENCY,
        prices=[LabeledPrice(label=f"{pkg['tokens']} Tokens", amount=pkg["stars"])],
    )


async def handle_pre_checkout(pre_checkout: PreCheckoutQuery) -> None:
    """Approve pre-checkout query."""
    await pre_checkout.answer(ok=True)


async def handle_successful_payment(message: Message, bot: Bot) -> None:
    """Handle successful payment — add tokens to user."""
    if message.from_user is None or message.successful_payment is None:
        return
    user_id = str(message.from_user.id)
    payment = message.successful_payment

    result = await award_tokens(user_id, payment.invoice_payload, payment.total_amount)
    await check_and_send_alerts(bot, credits_just_sold=result.tokens_added)

    await bot.send_message(
        chat_id=message.chat.id,
        text=f"Tokens added: +{result.tokens_added}\nBalance: {result.new_total_balance}",
    )


async def balance_command(event: EventLike, bot: Bot) -> None:
    """Show detailed credit balance."""
    if event.from_user is None:
        return
    chat_id = get_chat_id(event)
    language = await get_chat_language(chat_id)
    user_id = str(event.from_user.id)

    free, purchased = await get_credits(user_id)
    total = free + purchased

    month = current_month_key()
    usage = await UserMonthlyUsage.find_one(
        UserMonthlyUsage.user_id == user_id,
        UserMonthlyUsage.month_key == month,
    )

    text = (
        translates["balance_detailed"]
        .get(language, translates["balance_detailed"]["en"])
        .format(
            total=total,
            free=free,
            free_max=settings.free_monthly_tokens,
            purchased=purchased,
            month_transcriptions=usage.transcriptions if usage else 0,
            month_audio=_format_duration(usage.audio_seconds if usage else 0),
            month_tokens=usage.tokens_used if usage else 0,
        )
    )

    if isinstance(event, Message):
        target_chat_id: int = event.chat.id
    elif isinstance(event.message, Message):
        target_chat_id = event.message.chat.id
    else:
        return
    await bot.send_message(chat_id=target_chat_id, text=text)
