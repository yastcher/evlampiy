"""Telegram Stars payment handlers."""

import logging

from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes

from src import const
from src.config import settings
from src.credits import add_credits, get_credits, increment_payment_stats

logger = logging.getLogger(__name__)

INVOICE_TITLE = "Voice Credits"
INVOICE_DESCRIPTION = "Credits for voice message transcription"
INVOICE_PAYLOAD = "buy_credits"
DEFAULT_STAR_AMOUNT = 5


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send invoice for buying credits with Telegram Stars."""
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=INVOICE_TITLE,
        description=INVOICE_DESCRIPTION,
        payload=INVOICE_PAYLOAD,
        currency=const.TELEGRAM_STARS_CURRENCY,
        prices=[LabeledPrice("Credits", DEFAULT_STAR_AMOUNT)],
    )


async def handle_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve pre-checkout query."""
    await update.pre_checkout_query.answer(ok=True)


async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment — add credits to user."""
    user_id = update.effective_user.id
    payment = update.message.successful_payment
    credits_to_add = payment.total_amount * settings.credits_per_star

    new_balance = await add_credits(user_id, credits_to_add)
    await increment_payment_stats(credits_to_add)
    logger.info("User %s purchased %s credits, new balance: %s", user_id, credits_to_add, new_balance)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Credits added: +{credits_to_add}\nBalance: {new_balance}",
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current credit balance."""
    user_id = update.effective_user.id
    credits = await get_credits(user_id)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Balance: {credits} credits",
    )
