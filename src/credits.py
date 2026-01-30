"""Credit system for monetization."""

import hashlib
from datetime import datetime, timezone

from src.config import settings
from src.dto import MonthlyStats, UsedTrial, UserCredits, UserTier


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()


def is_vip_user(user_id: str) -> bool:
    return user_id in settings.vip_user_ids


def is_admin_user(user_id: str) -> bool:
    return user_id in settings.admin_user_ids


def has_unlimited_access(user_id: str) -> bool:
    return is_vip_user(user_id) or is_admin_user(user_id)


async def get_user_tier(user_id: str) -> UserTier:
    if is_vip_user(user_id) or is_admin_user(user_id):
        return UserTier.VIP
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if record and record.tier == UserTier.PAID:
        return UserTier.PAID
    return UserTier.FREE


async def get_credits(user_id: str) -> int:
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        return 0
    return record.credits


async def add_credits(user_id: str, amount: int) -> int:
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(
            user_id=user_id,
            credits=amount,
            tier=UserTier.PAID,
            total_credits_purchased=amount,
        )
        await record.insert()
    else:
        record.credits += amount
        record.tier = UserTier.PAID
        record.total_credits_purchased += amount
        await record.save()
    return record.credits


async def deduct_credits(user_id: str, amount: int) -> bool:
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record or record.credits < amount:
        return False
    record.credits -= amount
    record.total_credits_spent += amount
    await record.save()
    return True


async def grant_initial_credits_if_eligible(user_id: str) -> bool:
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


async def can_perform_operation(user_id: str, cost: int) -> tuple[bool, str]:
    if has_unlimited_access(user_id):
        return True, ""

    credits = await get_credits(user_id)
    if credits >= cost:
        return True, ""

    return False, "insufficient_credits"


async def increment_user_stats(user_id: str, audio_seconds: int = 0):
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(
            user_id=user_id,
            total_transcriptions=1,
            total_audio_seconds=audio_seconds,
        )
        await record.insert()
    else:
        record.total_transcriptions += 1
        record.total_audio_seconds += audio_seconds
        await record.save()


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


async def get_monthly_stats(month: str) -> MonthlyStats | None:
    return await MonthlyStats.find_one(MonthlyStats.month_key == month)
