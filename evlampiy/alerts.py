"""Admin alerts: the month's first payment, revenue milestones, and Wit usage.

They go out through the Telegram bot `register_admin_bot` takes when the Telegram side
starts, so a voice message from WhatsApp raises the Wit alerts too.
"""

import contextlib
import logging

import pymongo.errors
from aiogram import Bot

from evlampiy import const
from evlampiy.config import settings
from evlampiy.credits import current_month_key, get_monthly_stats
from evlampiy.dto import AlertState
from evlampiy.wit_tracking import get_all_wit_usage_this_month

logger = logging.getLogger(__name__)

REVENUE_MILESTONES = [10, 50, 100, 500, 1000]


class _AdminBotHolder:
    """Holder for the bot that writes to the admins — avoids ``global`` keyword."""

    bot: Bot | None = None


admin_bot = _AdminBotHolder()


def register_admin_bot(bot: Bot) -> None:
    """Send the admin alerts through `bot` from now on."""
    admin_bot.bot = bot


async def send_admin_alert(message: str) -> None:
    bot = admin_bot.bot
    if bot is None:
        logger.warning("No Telegram bot registered for admin alerts, dropped: %s", message)
        return
    for admin_id in settings.admin_user_ids:
        try:
            await bot.send_message(chat_id=int(admin_id), text=message, parse_mode="HTML")
        except Exception as e:
            logger.error("Failed to send alert to admin %s: %s", admin_id, e)


async def _should_send_alert(alert_type: str, month: str) -> bool:
    existing = await AlertState.find_one(
        AlertState.alert_type == alert_type,
        AlertState.month_key == month,
    )
    return existing is None


async def _mark_alert_sent(alert_type: str, month: str) -> None:
    # Concurrent alert may already be marked — the unique index makes this a no-op.
    with contextlib.suppress(pymongo.errors.DuplicateKeyError):
        await AlertState(alert_type=alert_type, month_key=month).insert()


async def check_payment_alerts(stars_just_paid: int) -> None:
    """After a payment: the month's first payment, and any revenue milestone it crossed.

    Revenue is the Telegram Stars paid, not the tokens they bought: a package sells more
    tokens than Stars.
    """
    if not settings.admin_user_ids:
        return

    month = current_month_key()
    stats = await get_monthly_stats(month)
    if stats is None:
        return

    if stats.total_payments == 1 and await _should_send_alert("first_payment", month):
        await send_admin_alert("🎉 <b>First payment received!</b>\n\nCongratulations!")
        await _mark_alert_sent("first_payment", month)

    revenue = stats.total_stars * const.STAR_TO_DOLLAR
    previous = max(stats.total_stars - stars_just_paid, 0) * const.STAR_TO_DOLLAR
    for milestone in REVENUE_MILESTONES:
        alert_type = f"revenue_{milestone}"
        if previous < milestone <= revenue and await _should_send_alert(alert_type, month):
            await send_admin_alert(f"🎉 <b>Revenue milestone!</b>\n\nReached ${milestone}!")
            await _mark_alert_sent(alert_type, month)


async def check_wit_alerts() -> None:
    """After Wit use on either channel: a language past 80 % or 95 % of the monthly free limit."""
    if not settings.admin_user_ids:
        return

    month = current_month_key()
    wit_limit = settings.wit_free_monthly_limit
    usage_by_lang = await get_all_wit_usage_this_month()

    for lang, wit_usage in usage_by_lang.items():
        if wit_usage > wit_limit * 0.95:
            if await _should_send_alert(f"wit_95_{lang}", month):
                await send_admin_alert(
                    f"🚨 <b>Wit.ai CRITICAL ({lang})</b>\n\n"
                    f"Usage: {wit_usage:,} / {wit_limit:,} ({wit_usage / wit_limit * 100:.1f}%)\n\n"
                    f"Free tier almost exhausted!",
                )
                await _mark_alert_sent(f"wit_95_{lang}", month)
        elif wit_usage > wit_limit * 0.8 and await _should_send_alert(f"wit_80_{lang}", month):
            await send_admin_alert(
                f"⚠️ <b>Wit.ai Warning ({lang})</b>\n\n"
                f"Usage: {wit_usage:,} / {wit_limit:,} ({wit_usage / wit_limit * 100:.1f}%)",
            )
            await _mark_alert_sent(f"wit_80_{lang}", month)
