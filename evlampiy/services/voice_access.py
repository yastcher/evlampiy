"""Who may have a voice message transcribed, and what it costs: one path for both channels.

Telegram and WhatsApp (ADR-001) ask `admit_voice` before the pipeline runs and call
`settle_voice` after it. Framework-agnostic: each channel words a refusal its own way.
"""

import dataclasses
import enum

from evlampiy import const
from evlampiy.config import settings
from evlampiy.credits import (
    calculate_token_cost,
    can_perform_operation,
    deduct_credits,
    get_user_tier,
    has_unlimited_voice_access,
    increment_transcription_stats,
    increment_user_stats,
    is_blocked_user,
    record_groq_usage,
    record_user_usage,
)
from evlampiy.dto import UserTier
from evlampiy.types import Language, UserId
from evlampiy.wit_tracking import increment_wit_usage, is_wit_available


class Refusal(enum.Enum):
    """Why a voice message is not transcribed."""

    BLOCKED = enum.auto()
    NO_PROVIDER = enum.auto()
    NO_TOKENS = enum.auto()


@dataclasses.dataclass(frozen=True, slots=True)
class Admission:
    """A voice message may go through the pipeline, at this tier and with this provider."""

    tier: UserTier
    provider: str


def select_provider(
    tier: UserTier,
    wit_available: bool,
    preferred_provider: str | None = None,
) -> str | None:
    """Select transcription provider based on user tier, availability, and preference.

    Default for all tiers: Wit.ai. Paid tiers can override via preferred_provider.
    Free: preference ignored, Wit.ai only.
    Returns the provider name or ``None`` if no provider is available.
    """
    groq_available = bool(settings.groq_api_key)

    if tier == UserTier.FREE:
        return const.PROVIDER_WIT if wit_available else None

    if preferred_provider == const.PROVIDER_GROQ and groq_available:
        return const.PROVIDER_GROQ

    if preferred_provider == const.PROVIDER_WIT and wit_available:
        return const.PROVIDER_WIT

    if wit_available:
        return const.PROVIDER_WIT
    return const.PROVIDER_GROQ if groq_available else None


async def admit_voice(user_id: UserId, language: Language, preferred_provider: str | None) -> Admission | Refusal:
    """Whether `user_id` may have a voice message in `language` transcribed, and how.

    The block first, then a provider for the user's tier, then the tokens.
    """
    if await is_blocked_user(user_id):
        return Refusal.BLOCKED
    tier = await get_user_tier(user_id)
    provider = select_provider(tier, await is_wit_available(language), preferred_provider)
    if provider is None:
        return Refusal.NO_PROVIDER
    if not await has_unlimited_voice_access(user_id):
        has_tokens, _ = await can_perform_operation(user_id, 1)
        if not has_tokens:
            return Refusal.NO_TOKENS
    return Admission(tier=tier, provider=provider)


async def settle_voice(user_id: UserId, provider: str, language: Language, duration: int, wit_requests: int) -> bool:
    """Charge a transcribed message's tokens and count its use; True when the charge overdrew the balance."""
    overdraft = False
    if not await has_unlimited_voice_access(user_id):
        cost = calculate_token_cost(duration)
        charge = await deduct_credits(user_id, cost)
        await record_user_usage(user_id, duration, cost, charge.free_used, charge.purchased_used)
        overdraft = charge.overdraft
    if provider == const.PROVIDER_WIT:
        await increment_wit_usage(wit_requests, language=language)
    elif provider == const.PROVIDER_GROQ:
        await record_groq_usage(duration)
    await increment_transcription_stats()
    await increment_user_stats(user_id, audio_seconds=duration)
    return overdraft
