"""Account linking between Telegram and WhatsApp."""

import logging
import random
import typing
from datetime import datetime, timedelta, timezone

from src.dto import AccountLink, LinkAttempt, LinkCode

logger = logging.getLogger(__name__)

LINK_CODE_LENGTH = 6
LINK_CODE_TTL_SECONDS = 300  # 5 minutes
LINK_MAX_ATTEMPTS = 5
LINK_LOCKOUT_SECONDS = 300  # 5 minutes

LinkResult = typing.Literal["success", "invalid", "rate_limited"]


async def generate_link_code(telegram_user_id: str) -> str:
    """Generate a one-time code for linking WhatsApp account."""
    await LinkCode.find(LinkCode.telegram_user_id == telegram_user_id).delete()

    code = "".join(str(random.randint(0, 9)) for _ in range(LINK_CODE_LENGTH))
    await LinkCode(code=code, telegram_user_id=telegram_user_id).insert()

    return code


def _to_aware(dt: datetime) -> datetime:
    """Convert naive datetime to UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def _check_rate_limit(whatsapp_phone: str) -> LinkAttempt | None:
    """Check rate limit and return attempt record. Returns None if rate limited."""
    now = datetime.now(timezone.utc)
    attempt = await LinkAttempt.find_one(LinkAttempt.whatsapp_phone == whatsapp_phone)

    if not attempt:
        attempt = LinkAttempt(whatsapp_phone=whatsapp_phone)
        await attempt.insert()
        return attempt

    if attempt.locked_until:
        locked_until = _to_aware(attempt.locked_until)
        if now < locked_until:
            logger.warning("Rate limited: phone %s locked until %s", whatsapp_phone, locked_until)
            return None
        attempt.locked_until = None
        attempt.attempt_count = 0
        attempt.first_attempt_at = now

    first_attempt = _to_aware(attempt.first_attempt_at)
    if (now - first_attempt).total_seconds() > LINK_LOCKOUT_SECONDS:
        attempt.attempt_count = 0
        attempt.first_attempt_at = now

    return attempt


async def _record_failed_attempt(attempt: LinkAttempt) -> None:
    """Record failed attempt and lock if limit exceeded."""
    attempt.attempt_count += 1
    if attempt.attempt_count >= LINK_MAX_ATTEMPTS:
        attempt.locked_until = datetime.now(timezone.utc) + timedelta(seconds=LINK_LOCKOUT_SECONDS)
        logger.warning("Phone %s locked after %d failed attempts", attempt.whatsapp_phone, attempt.attempt_count)
    await attempt.save()


async def confirm_link(code: str, whatsapp_phone: str) -> LinkResult:
    """Confirm link using one-time code. Returns result status."""
    attempt = await _check_rate_limit(whatsapp_phone)
    if attempt is None:
        return "rate_limited"

    record = await LinkCode.find_one(LinkCode.code == code)
    if not record:
        await _record_failed_attempt(attempt)
        return "invalid"

    created_at = _to_aware(record.created_at)
    elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
    if elapsed > LINK_CODE_TTL_SECONDS:
        await record.delete()
        await _record_failed_attempt(attempt)
        return "invalid"

    telegram_user_id = record.telegram_user_id
    await record.delete()

    # Remove existing links for both sides (1:1 constraint)
    await AccountLink.find(AccountLink.telegram_user_id == telegram_user_id).delete()
    await AccountLink.find(AccountLink.whatsapp_phone == whatsapp_phone).delete()

    await AccountLink(
        telegram_user_id=telegram_user_id,
        whatsapp_phone=whatsapp_phone,
    ).insert()

    # Clear rate limit on success
    await attempt.delete()

    logger.info("Linked Telegram %s <-> WhatsApp %s", telegram_user_id, whatsapp_phone)
    return "success"


async def get_linked_telegram_id(whatsapp_phone: str) -> str | None:
    """Get Telegram user ID linked to WhatsApp phone."""
    record = await AccountLink.find_one(AccountLink.whatsapp_phone == whatsapp_phone)
    return record.telegram_user_id if record else None


async def get_linked_whatsapp(telegram_user_id: str) -> str | None:
    """Get WhatsApp phone linked to Telegram user ID."""
    record = await AccountLink.find_one(AccountLink.telegram_user_id == telegram_user_id)
    return record.whatsapp_phone if record else None


async def unlink(telegram_user_id: str) -> bool:
    """Remove link for Telegram user. Returns True if link existed."""
    record = await AccountLink.find_one(AccountLink.telegram_user_id == telegram_user_id)
    if not record:
        return False
    await record.delete()
    return True
