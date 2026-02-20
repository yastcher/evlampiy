"""Credit system for monetization."""

import dataclasses
import datetime
import hashlib
import math

from src import const
from src.config import settings
from src.dto import MonthlyStats, UsedTrial, UserCredits, UserMonthlyUsage, UserTier
from src.mongo import has_role


@dataclasses.dataclass
class DeductResult:
    free_used: int
    purchased_used: int
    overdraft: bool  # True = balance was insufficient, deducted what was available


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()


def calculate_token_cost(duration_seconds: int) -> int:
    """Calculate token cost based on audio duration. 1 token = 20 seconds."""
    return max(1, math.ceil(duration_seconds / const.SECONDS_PER_TOKEN))


async def is_blocked_user(user_id: str) -> bool:
    """Check if user is blocked."""
    return await has_role(user_id, const.ROLE_BLOCKED)


async def is_vip_user(user_id: str) -> bool:
    """Check VIP status: DB first, then env fallback."""
    if await has_role(user_id, const.ROLE_VIP):
        return True
    return user_id in settings.vip_user_ids


def is_admin_user(user_id: str) -> bool:
    return user_id in settings.admin_user_ids


async def is_tester_user(user_id: str) -> bool:
    return await has_role(user_id, const.ROLE_TESTER)


async def has_unlimited_access(user_id: str) -> bool:
    """VIP or admin — unlimited everything."""
    return await is_vip_user(user_id) or is_admin_user(user_id)


async def has_unlimited_voice_access(user_id: str) -> bool:
    """VIP, admin, or tester — unlimited voice transcription."""
    if await has_unlimited_access(user_id):
        return True
    return await is_tester_user(user_id)


async def get_user_tier(user_id: str) -> UserTier:
    if await is_vip_user(user_id) or is_admin_user(user_id):
        return UserTier.VIP
    if await is_tester_user(user_id):
        return UserTier.TESTER
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if record and record.tier == UserTier.PAID:
        return UserTier.PAID
    return UserTier.FREE


def current_month_key() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m")


# --- Lazy reset ---


async def _ensure_fresh_free_credits(record: UserCredits) -> UserCredits:
    """Lazy reset: if month is not current, refresh free_credits."""
    current = current_month_key()
    if record.free_credits_month != current:
        record.free_credits = settings.free_monthly_tokens
        record.free_credits_month = current
        await record.save()
    return record


async def _get_or_create_user_credits(user_id: str) -> UserCredits:
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(
            user_id=user_id,
            free_credits=settings.free_monthly_tokens,
            free_credits_month=current_month_key(),
        )
        await record.insert()
    return record


# --- Credit queries ---


async def get_credits(user_id: str) -> tuple[int, int]:
    """Return (free_credits, purchased_credits) with lazy reset."""
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        return (settings.free_monthly_tokens, 0)
    record = await _ensure_fresh_free_credits(record)
    return (record.free_credits, record.purchased_credits)


async def get_total_credits(user_id: str) -> int:
    """Return total available credits (free + purchased)."""
    free, purchased = await get_credits(user_id)
    return free + purchased


async def can_perform_operation(user_id: str, cost: int) -> tuple[bool, str]:
    if await has_unlimited_access(user_id):
        return True, ""
    free, purchased = await get_credits(user_id)
    if free + purchased >= cost:
        return True, ""
    return False, "insufficient_credits"


# --- Credit mutations ---


async def add_credits(user_id: str, amount: int) -> int:
    """Add purchased credits. Returns new purchased balance."""
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(
            user_id=user_id,
            purchased_credits=amount,
            tier=UserTier.PAID,
            total_credits_purchased=amount,
            free_credits=settings.free_monthly_tokens,
            free_credits_month=current_month_key(),
        )
        await record.insert()
    else:
        record.purchased_credits += amount
        record.tier = UserTier.PAID
        record.total_credits_purchased += amount
        await record.save()
    return record.purchased_credits


async def admin_add_credits(user_id: str, amount: int) -> int:
    """Add credits without changing tier (for admin top-ups)."""
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(
            user_id=user_id,
            purchased_credits=amount,
            free_credits=settings.free_monthly_tokens,
            free_credits_month=current_month_key(),
        )
        await record.insert()
    else:
        record.purchased_credits += amount
        await record.save()
    return record.purchased_credits


async def deduct_credits(user_id: str, cost: int) -> DeductResult:
    """Deduct tokens: free first, then purchased.

    Never goes below 0. If not enough — deducts what's available (overdraft).
    """
    record = await _get_or_create_user_credits(user_id)
    record = await _ensure_fresh_free_credits(record)

    total_available = record.free_credits + record.purchased_credits
    actual_cost = min(cost, total_available)

    free_used = min(record.free_credits, actual_cost)
    purchased_used = actual_cost - free_used

    record.free_credits -= free_used
    record.purchased_credits -= purchased_used
    record.total_tokens_used += actual_cost
    record.total_credits_spent += actual_cost
    await record.save()

    return DeductResult(
        free_used=free_used,
        purchased_used=purchased_used,
        overdraft=total_available < cost,
    )


# --- Legacy (kept for backward compat, no longer called from handlers) ---


async def grant_initial_credits_if_eligible(user_id: str) -> bool:
    user_hash = hash_user_id(user_id)
    existing = await UsedTrial.find_one(UsedTrial.user_hash == user_hash)
    if existing:
        return False

    await UsedTrial(user_hash=user_hash).insert()

    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(user_id=user_id, purchased_credits=3)
        await record.insert()
    else:
        record.purchased_credits += 3
        await record.save()
    return True


# --- Usage tracking ---


async def increment_user_stats(user_id: str, audio_seconds: int = 0):
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        record = UserCredits(
            user_id=user_id,
            total_transcriptions=1,
            total_audio_seconds=audio_seconds,
            free_credits=settings.free_monthly_tokens,
            free_credits_month=current_month_key(),
        )
        await record.insert()
    else:
        record.total_transcriptions += 1
        record.total_audio_seconds += audio_seconds
        await record.save()


async def record_user_usage(
    user_id: str,
    audio_seconds: int,
    tokens: int,
    free_used: int,
    purchased_used: int,
):
    """Record per-user monthly usage."""
    month = current_month_key()
    record = await UserMonthlyUsage.find_one(
        UserMonthlyUsage.user_id == user_id,
        UserMonthlyUsage.month_key == month,
    )
    if not record:
        record = UserMonthlyUsage(user_id=user_id, month_key=month)
        await record.insert()

    record.transcriptions += 1
    record.audio_seconds += audio_seconds
    record.tokens_used += tokens
    record.free_tokens_used += free_used
    record.purchased_tokens_used += purchased_used
    await record.save()


# --- System stats ---


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
