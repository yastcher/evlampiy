"""Admin alert service."""

import logging

from telegram import Bot

from src import const
from src.config import settings
from src.credits import current_month_key, get_monthly_stats
from src.dto import AlertState
from src.wit_tracking import get_all_wit_usage_this_month

logger = logging.getLogger(__name__)

REVENUE_MILESTONES = [10, 50, 100, 500, 1000]


async def send_admin_alert(bot: Bot, message: str):
    for admin_id in settings.admin_user_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=message, parse_mode="HTML")
        except Exception as e:
            logger.error("Failed to send alert to admin %s: %s", admin_id, e)


async def _should_send_alert(alert_type: str, month: str) -> bool:
    existing = await AlertState.find_one(
        AlertState.alert_type == alert_type,
        AlertState.month_key == month,
    )
    return existing is None


async def _mark_alert_sent(alert_type: str, month: str):
    await AlertState(alert_type=alert_type, month_key=month).insert()


async def check_and_send_alerts(bot: Bot, credits_just_sold: int = 1):
    if not settings.admin_user_ids:
        return

    month = current_month_key()
    stats = await get_monthly_stats(month)

    if stats and stats.total_payments == 1:
        if await _should_send_alert("first_payment", month):
            await send_admin_alert(bot, "🎉 <b>First payment received!</b>\n\nCongratulations!")
            await _mark_alert_sent("first_payment", month)

        revenue = stats.total_credits_sold * const.STAR_TO_DOLLAR
        for milestone in REVENUE_MILESTONES:
            prev_revenue = (
                (stats.total_credits_sold - credits_just_sold) * const.STAR_TO_DOLLAR
                if stats.total_credits_sold >= credits_just_sold
                else 0
            )
            if prev_revenue < milestone <= revenue:
                alert_type = f"revenue_{milestone}"
                if await _should_send_alert(alert_type, month):
                    await send_admin_alert(
                        bot, f"🎉 <b>Revenue milestone!</b>\n\nReached ${milestone}!"
                    )
                    await _mark_alert_sent(alert_type, month)

    wit_limit = settings.wit_free_monthly_limit
    usage_by_lang = await get_all_wit_usage_this_month()

    for lang, wit_usage in usage_by_lang.items():
        if wit_usage > wit_limit * 0.95:
            if await _should_send_alert(f"wit_95_{lang}", month):
                await send_admin_alert(
                    bot,
                    f"🚨 <b>Wit.ai CRITICAL ({lang})</b>\n\n"
                    f"Usage: {wit_usage:,} / {wit_limit:,} ({wit_usage / wit_limit * 100:.1f}%)\n\n"
                    f"Free tier almost exhausted!",
                )
                await _mark_alert_sent(f"wit_95_{lang}", month)
        elif wit_usage > wit_limit * 0.8 and await _should_send_alert(f"wit_80_{lang}", month):
            await send_admin_alert(
                bot,
                f"⚠️ <b>Wit.ai Warning ({lang})</b>\n\n"
                f"Usage: {wit_usage:,} / {wit_limit:,} ({wit_usage / wit_limit * 100:.1f}%)",
            )
            await _mark_alert_sent(f"wit_80_{lang}", month)
