"""Telegram Stars payment handlers."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import ContextTypes

from src import const
from src.alerts import check_and_send_alerts
from src.config import settings
from src.credits import (
    add_credits,
    current_month_key,
    get_credits,
    get_total_credits,
    increment_payment_stats,
)
from src.dto import UserMonthlyUsage
from src.localization import translates
from src.mongo import get_chat_language
from src.telegram.chat_params import get_chat_id

logger = logging.getLogger(__name__)

CREDIT_PACKAGES = [
    {"name": "Small", "stars": 10, "tokens": 10, "callback": "buy_pkg_0"},
    {"name": "Medium", "stars": 25, "tokens": 30, "callback": "buy_pkg_1"},
    {"name": "Large", "stars": 50, "tokens": 65, "callback": "buy_pkg_2"},
    {"name": "XL", "stars": 100, "tokens": 140, "callback": "buy_pkg_3"},
]


def _format_duration(seconds: int) -> str:
    """Format seconds as 'Xm Ys'."""
    minutes = seconds // 60
    secs = seconds % 60
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show credit packages for purchase."""
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    keyboard = []
    for pkg in CREDIT_PACKAGES:
        label = f"{pkg['name']} — {pkg['tokens']} tokens ({pkg['stars']}★)"
        keyboard.append([InlineKeyboardButton(label, callback_data=pkg["callback"])])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = translates["buy_packages_prompt"].get(language, translates["buy_packages_prompt"]["en"])
    await update.message.reply_text(text, reply_markup=reply_markup)


async def buy_package_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle package selection and send invoice."""
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[-1])
    pkg = CREDIT_PACKAGES[idx]

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=f"{pkg['name']} Token Package",
        description=f"{pkg['tokens']} tokens for voice transcription",
        payload=f"buy_tokens_{idx}",
        currency=const.TELEGRAM_STARS_CURRENCY,
        prices=[LabeledPrice(f"{pkg['tokens']} Tokens", pkg["stars"])],
    )


async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve pre-checkout query."""
    await update.pre_checkout_query.answer(ok=True)


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment — add tokens to user."""
    user_id = str(update.effective_user.id)
    payment = update.message.successful_payment

    # Determine tokens from payload
    payload = payment.invoice_payload
    if payload.startswith("buy_tokens_"):
        idx = int(payload.split("_")[-1])
        tokens_to_add = CREDIT_PACKAGES[idx]["tokens"]
    else:
        # Legacy fallback
        tokens_to_add = payment.total_amount

    new_purchased = await add_credits(user_id, tokens_to_add)
    await increment_payment_stats(tokens_to_add)
    await check_and_send_alerts(context.bot, credits_just_sold=tokens_to_add)
    logger.info(
        "User %s purchased %s tokens, purchased balance: %s",
        user_id,
        tokens_to_add,
        new_purchased,
    )

    total = await get_total_credits(user_id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Tokens added: +{tokens_to_add}\nBalance: {total}",
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed credit balance."""
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    user_id = str(update.effective_user.id)

    free, purchased = await get_credits(user_id)
    total = free + purchased

    # Get monthly usage
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
    )
