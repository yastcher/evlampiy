"""Wit.ai monthly usage tracking."""

from src.config import settings
from src.credits import current_month_key
from src.dto import WitUsageStats


async def increment_wit_usage(count: int = 1) -> int:
    month_key = current_month_key()
    record = await WitUsageStats.find_one(WitUsageStats.month_key == month_key)
    if not record:
        record = WitUsageStats(month_key=month_key, request_count=count)
        await record.insert()
    else:
        record.request_count += count
        await record.save()
    return record.request_count


async def get_wit_usage_this_month() -> int:
    month_key = current_month_key()
    record = await WitUsageStats.find_one(WitUsageStats.month_key == month_key)
    if not record:
        return 0
    return record.request_count


async def is_wit_available() -> bool:
    usage = await get_wit_usage_this_month()
    return usage < settings.wit_free_monthly_limit
