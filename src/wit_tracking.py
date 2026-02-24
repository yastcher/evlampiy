"""Wit.ai monthly usage tracking."""

from src.config import settings
from src.credits import current_month_key
from src.dto import WitUsageStats
from src.types import Language


async def increment_wit_usage(count: int = 1, language: Language = "ru") -> int:
    month_key = current_month_key()
    record = await WitUsageStats.find_one(
        WitUsageStats.month_key == month_key,
        WitUsageStats.language == language,
    )
    if not record:
        record = WitUsageStats(month_key=month_key, language=language, request_count=count)
        await record.insert()
    else:
        record.request_count += count
        await record.save()
    return record.request_count


async def get_wit_usage_this_month(language: Language) -> int:
    month_key = current_month_key()
    record = await WitUsageStats.find_one(
        WitUsageStats.month_key == month_key,
        WitUsageStats.language == language,
    )
    if not record:
        return 0
    return record.request_count


async def get_all_wit_usage_this_month() -> dict[str, int]:
    """Return per-language request counts for the current month."""
    month_key = current_month_key()
    records = await WitUsageStats.find(WitUsageStats.month_key == month_key).to_list()
    return {r.language: r.request_count for r in records if r.language}


async def is_wit_available(language: Language) -> bool:
    usage = await get_wit_usage_this_month(language)
    return usage < settings.wit_free_monthly_limit
