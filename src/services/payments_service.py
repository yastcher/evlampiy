"""Telegram-Stars payment use-case service. Framework-agnostic — no aiogram."""

import dataclasses
import logging
import typing

import pymongo.errors

from src.credits import add_credits, get_total_credits, increment_payment_stats
from src.dto import ProcessedPayment
from src.types import UserId

logger = logging.getLogger(__name__)

PAYLOAD_PREFIX = "buy_tokens_"


class CreditPackage(typing.TypedDict):
    """A purchasable token package."""

    name: str
    stars: int
    tokens: int


CREDIT_PACKAGES: list[CreditPackage] = [
    {"name": "Small", "stars": 10, "tokens": 10},
    {"name": "Medium", "stars": 25, "tokens": 30},
    {"name": "Large", "stars": 50, "tokens": 65},
    {"name": "XL", "stars": 100, "tokens": 140},
]


@dataclasses.dataclass(frozen=True, slots=True)
class AwardResult:
    """Outcome of crediting a successful payment to a user."""

    tokens_added: int
    new_total_balance: int


def package_payload(idx: int) -> str:
    """Build the invoice payload for the package at index ``idx``."""
    return f"{PAYLOAD_PREFIX}{idx}"


def tokens_for_payload(payload: str, total_amount: int) -> int:
    """Resolve how many tokens to award for a successful payment.

    The canonical path: payload is ``buy_tokens_<idx>`` and we look up the package's
    ``tokens`` field. Legacy / unrecognised payloads fall back to the raw stars amount,
    so a manual top-up still credits something rather than dropping silently.
    """
    if payload.startswith(PAYLOAD_PREFIX):
        idx = int(payload.rsplit("_", maxsplit=1)[-1])
        return CREDIT_PACKAGES[idx]["tokens"]
    return total_amount


async def _claim_charge(user_id: UserId, charge_id: str) -> bool:
    """Claim a payment charge as an idempotency key. Returns False if already claimed.

    Claim-first (before crediting): a Telegram redelivery is rejected, so we never
    double-credit. The tiny window where a crash leaves a charge claimed-but-uncredited is
    recoverable via an admin top-up — preferable to silently granting paid tokens twice.
    """
    try:
        await ProcessedPayment(charge_id=charge_id, user_id=user_id).insert()
        return True
    except pymongo.errors.DuplicateKeyError:
        return False


async def award_tokens(user_id: UserId, payload: str, total_amount: int, charge_id: str) -> AwardResult | None:
    """Credit tokens for a successful Telegram-Stars payment, exactly once.

    Returns ``None`` when ``charge_id`` was already processed — Telegram can redeliver the
    ``successful_payment`` update, and the caller must not re-credit or re-notify. Otherwise
    returns the tokens awarded and the user's new total balance; the caller (adapter) sends
    the confirmation message and admin alerts, which need a framework-specific Bot handle.
    """
    if not await _claim_charge(user_id, charge_id):
        logger.info("Duplicate payment %s for user %s ignored", charge_id, user_id)
        return None

    tokens_to_add = tokens_for_payload(payload, total_amount)
    new_purchased = await add_credits(user_id, tokens_to_add)
    await increment_payment_stats(tokens_to_add)
    logger.info(
        "User %s purchased %s tokens, purchased balance: %s",
        user_id,
        tokens_to_add,
        new_purchased,
    )
    total = await get_total_credits(user_id)
    return AwardResult(tokens_added=tokens_to_add, new_total_balance=total)
