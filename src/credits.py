"""Credit system for monetization."""

import dataclasses
import datetime
import hashlib
import math
import typing

import pymongo.errors
from beanie.odm.operators.update.general import Inc, Set

from src import const
from src.config import settings
from src.dto import MonthlyStats, UsedTrial, UserCredits, UserMonthlyUsage, UserTier
from src.mongo import get_or_create, has_role
from src.types import UserId


@dataclasses.dataclass
class DeductResult:
    free_used: int
    purchased_used: int
    overdraft: bool  # True = balance was insufficient, deducted what was available


def hash_user_id(user_id: UserId) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()


def calculate_token_cost(duration_seconds: int) -> int:
    """Calculate token cost based on audio duration. 1 token = 20 seconds."""
    return max(1, math.ceil(duration_seconds / const.SECONDS_PER_TOKEN))


async def is_blocked_user(user_id: UserId) -> bool:
    """Check if user is blocked."""
    return await has_role(user_id, const.ROLE_BLOCKED)


async def is_vip_user(user_id: UserId) -> bool:
    """Check VIP status: DB first, then env fallback."""
    if await has_role(user_id, const.ROLE_VIP):
        return True
    return user_id in settings.vip_user_ids


def is_admin_user(user_id: UserId) -> bool:
    return user_id in settings.admin_user_ids


async def is_tester_user(user_id: UserId) -> bool:
    return await has_role(user_id, const.ROLE_TESTER)


async def has_unlimited_access(user_id: UserId) -> bool:
    """VIP or admin — unlimited everything."""
    return await is_vip_user(user_id) or is_admin_user(user_id)


async def has_unlimited_voice_access(user_id: UserId) -> bool:
    """VIP, admin, or tester — unlimited voice transcription."""
    if await has_unlimited_access(user_id):
        return True
    return await is_tester_user(user_id)


async def get_user_tier(user_id: UserId) -> UserTier:
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


def _effective_free(record: UserCredits, month: str) -> int:
    """Free credits after the lazy monthly reset, without persisting it."""
    return record.free_credits if record.free_credits_month == month else settings.free_monthly_tokens


async def _get_or_create_user_credits(user_id: UserId) -> UserCredits:
    return await get_or_create(
        lambda: UserCredits.find_one(UserCredits.user_id == user_id),
        lambda: UserCredits(
            user_id=user_id,
            free_credits=settings.free_monthly_tokens,
            free_credits_month=current_month_key(),
        ),
    )


# --- Credit queries ---


async def get_credits(user_id: UserId) -> tuple[int, int]:
    """Return (free_credits, purchased_credits).

    Pure read: the monthly free reset is reflected in the returned value but persisted
    lazily on the next spend (`deduct_credits`), so a read never clobbers a deduction.
    """
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    if not record:
        return (settings.free_monthly_tokens, 0)
    return (_effective_free(record, current_month_key()), record.purchased_credits)


async def get_total_credits(user_id: UserId) -> int:
    """Return total available credits (free + purchased)."""
    free, purchased = await get_credits(user_id)
    return free + purchased


async def can_perform_operation(user_id: UserId, cost: int) -> tuple[bool, str]:
    if await has_unlimited_access(user_id):
        return True, ""
    free, purchased = await get_credits(user_id)
    if free + purchased >= cost:
        return True, ""
    return False, "insufficient_credits"


# --- Credit mutations ---


async def add_credits(user_id: UserId, amount: int) -> int:
    """Add purchased credits (atomic). Returns new purchased balance."""
    await UserCredits.find_one(UserCredits.user_id == user_id).upsert(
        Inc({UserCredits.purchased_credits: amount, UserCredits.total_credits_purchased: amount}),
        Set({UserCredits.tier: UserTier.PAID}),
        on_insert=UserCredits(
            user_id=user_id,
            purchased_credits=amount,
            total_credits_purchased=amount,
            tier=UserTier.PAID,
            free_credits=settings.free_monthly_tokens,
            free_credits_month=current_month_key(),
        ),
    )
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    return record.purchased_credits if record else amount


async def admin_add_credits(user_id: UserId, amount: int) -> int:
    """Add credits without changing tier, for admin top-ups (atomic)."""
    await UserCredits.find_one(UserCredits.user_id == user_id).upsert(
        Inc({UserCredits.purchased_credits: amount}),
        on_insert=UserCredits(
            user_id=user_id,
            purchased_credits=amount,
            free_credits=settings.free_monthly_tokens,
            free_credits_month=current_month_key(),
        ),
    )
    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    return record.purchased_credits if record else amount


def _deduct_pipeline(cost: int, month: str, monthly: int) -> list[dict[str, typing.Any]]:
    """Aggregation pipeline: deduct ``cost`` (free first, then purchased, floored at 0),
    applying the monthly free reset inline so the whole deduction is one atomic update."""
    effective_free = {"$cond": [{"$eq": ["$free_credits_month", month]}, "$free_credits", monthly]}
    actual_cost = {"$min": [cost, {"$add": [effective_free, "$purchased_credits"]}]}
    free_used = {"$min": [effective_free, actual_cost]}
    return [
        {
            "$set": {
                "free_credits": {"$subtract": [effective_free, free_used]},
                "purchased_credits": {"$subtract": ["$purchased_credits", {"$subtract": [actual_cost, free_used]}]},
                "free_credits_month": month,
                "total_tokens_used": {"$add": ["$total_tokens_used", actual_cost]},
                "total_credits_spent": {"$add": ["$total_credits_spent", actual_cost]},
            }
        }
    ]


async def deduct_credits(user_id: UserId, cost: int) -> DeductResult:
    """Deduct tokens: free first, then purchased. Never below 0; over-spend is capped.

    The balance mutation is a single atomic server-side update (no lost updates). The
    returned free/purchased split is derived from the pre-deduction snapshot; under real
    concurrency the split may differ slightly from what was atomically deducted, but the
    balance itself stays correct (the split only feeds usage stats, not the balance).
    """
    record = await _get_or_create_user_credits(user_id)
    month = current_month_key()

    effective_free = _effective_free(record, month)
    total_available = effective_free + record.purchased_credits
    actual_cost = min(cost, total_available)
    free_used = min(effective_free, actual_cost)

    await UserCredits.get_pymongo_collection().update_one(
        {"user_id": user_id},
        _deduct_pipeline(cost, month, settings.free_monthly_tokens),
    )

    return DeductResult(
        free_used=free_used,
        purchased_used=actual_cost - free_used,
        overdraft=total_available < cost,
    )


# --- Legacy (kept for backward compat, no longer called from handlers) ---


async def grant_initial_credits_if_eligible(user_id: UserId) -> bool:
    user_hash = hash_user_id(user_id)
    existing = await UsedTrial.find_one(UsedTrial.user_hash == user_hash)
    if existing:
        return False

    try:
        await UsedTrial(user_hash=user_hash).insert()
    except pymongo.errors.DuplicateKeyError:
        # A concurrent grant already claimed the trial for this user.
        return False

    await UserCredits.find_one(UserCredits.user_id == user_id).upsert(
        Inc({UserCredits.purchased_credits: 3}),
        on_insert=UserCredits(user_id=user_id, purchased_credits=3),
    )
    return True


# --- Usage tracking ---


async def increment_user_stats(user_id: UserId, audio_seconds: int = 0) -> None:
    await UserCredits.find_one(UserCredits.user_id == user_id).upsert(
        Inc({UserCredits.total_transcriptions: 1, UserCredits.total_audio_seconds: audio_seconds}),
        on_insert=UserCredits(
            user_id=user_id,
            total_transcriptions=1,
            total_audio_seconds=audio_seconds,
            free_credits=settings.free_monthly_tokens,
            free_credits_month=current_month_key(),
        ),
    )


async def record_user_usage(
    user_id: UserId,
    audio_seconds: int,
    tokens: int,
    free_used: int,
    purchased_used: int,
) -> None:
    """Record per-user monthly usage (atomic accumulation)."""
    month = current_month_key()
    await UserMonthlyUsage.find_one(
        UserMonthlyUsage.user_id == user_id,
        UserMonthlyUsage.month_key == month,
    ).upsert(
        Inc(
            {
                UserMonthlyUsage.transcriptions: 1,
                UserMonthlyUsage.audio_seconds: audio_seconds,
                UserMonthlyUsage.tokens_used: tokens,
                UserMonthlyUsage.free_tokens_used: free_used,
                UserMonthlyUsage.purchased_tokens_used: purchased_used,
            }
        ),
        on_insert=UserMonthlyUsage(
            user_id=user_id,
            month_key=month,
            transcriptions=1,
            audio_seconds=audio_seconds,
            tokens_used=tokens,
            free_tokens_used=free_used,
            purchased_tokens_used=purchased_used,
        ),
    )


# --- System stats ---


async def increment_transcription_stats() -> None:
    month = current_month_key()
    await MonthlyStats.find_one(MonthlyStats.month_key == month).upsert(
        Inc({MonthlyStats.total_transcriptions: 1}),
        on_insert=MonthlyStats(month_key=month, total_transcriptions=1),
    )


async def record_groq_usage(duration_seconds: int) -> None:
    month = current_month_key()
    await MonthlyStats.find_one(MonthlyStats.month_key == month).upsert(
        Inc({MonthlyStats.groq_audio_seconds: duration_seconds}),
        on_insert=MonthlyStats(month_key=month, groq_audio_seconds=duration_seconds),
    )


async def increment_payment_stats(credits_sold: int) -> None:
    month = current_month_key()
    await MonthlyStats.find_one(MonthlyStats.month_key == month).upsert(
        Inc({MonthlyStats.total_payments: 1, MonthlyStats.total_credits_sold: credits_sold}),
        on_insert=MonthlyStats(month_key=month, total_payments=1, total_credits_sold=credits_sold),
    )


async def get_monthly_stats(month: str) -> MonthlyStats | None:
    return await MonthlyStats.find_one(MonthlyStats.month_key == month)
