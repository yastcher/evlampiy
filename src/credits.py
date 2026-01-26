"""Credit system for monetization."""

import hashlib
from datetime import datetime, timezone

from src.config import settings
from src.dto import MonthlyStats, UsedTrial, UserCredits, UserTier


def hash_user_id(user_id: int) -> str:
    return hashlib.sha256(str(user_id).encode()).hexdigest()


def is_vip_user(user_id: int) -> bool:
    return user_id in settings.vip_user_ids


async def get_user_tier(user_id: int) -> UserTier:
    if is_vip_user(user_id):
        return UserTier.VIP
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if record and record.tier == UserTier.PAID:
        return UserTier.PAID
    return UserTier.FREE


async def get_credits(user_id: int) -> int:
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        return 0
    return record.credits


async def add_credits(user_id: int, amount: int) -> int:
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(user_id=user_id, credits=amount, tier=UserTier.PAID)
        await record.insert()
    else:
        record.credits += amount
        record.tier = UserTier.PAID
        await record.save()
    return record.credits


async def deduct_credits(user_id: int, amount: int) -> bool:
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record or record.credits < amount:
        return False
    record.credits -= amount
    await record.save()
    return True


async def grant_initial_credits_if_eligible(user_id: int) -> bool:
    user_hash = hash_user_id(user_id)
    existing = await UsedTrial.find_one(UsedTrial.user_hash == user_hash)
    if existing:
        return False

    await UsedTrial(user_hash=user_hash).insert()

    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(user_id=user_id, credits=settings.initial_credits)
        await record.insert()
    else:
        record.credits += settings.initial_credits
        await record.save()
    return True


async def can_perform_operation(user_id: int, cost: int) -> tuple[bool, str]:
    if is_vip_user(user_id):
        return True, ""

    credits = await get_credits(user_id)
    if credits >= cost:
        return True, ""

    return False, "insufficient_credits"


def current_month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def _get_or_create_monthly_stats() -> MonthlyStats:
    month_key = current_month_key()
    record = await MonthlyStats.find_one(MonthlyStats.month_key == month_key)
    if not record:
        record = MonthlyStats(month_key=month_key)
        await record.insert()
    return record


async def increment_transcription_stats():
    record = await _get_or_create_monthly_stats()
    record.total_transcriptions += 1
    await record.save()


async def record_groq_usage(duration_seconds: int):
    record = await _get_or_create_monthly_stats()
    record.groq_audio_seconds += duration_seconds
    await record.save()


async def increment_payment_stats(credits_sold: int):
    record = await _get_or_create_monthly_stats()
    record.total_payments += 1
    record.total_credits_sold += credits_sold
    await record.save()
