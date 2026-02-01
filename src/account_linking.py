"""Account linking between Telegram and WhatsApp."""

import logging
import random
from datetime import datetime, timezone

from src.dto import AccountLink, LinkCode

logger = logging.getLogger(__name__)

LINK_CODE_LENGTH = 6
LINK_CODE_TTL_SECONDS = 300  # 5 minutes


async def generate_link_code(telegram_user_id: str) -> str:
    """Generate a one-time code for linking WhatsApp account."""
    await LinkCode.find(LinkCode.telegram_user_id == telegram_user_id).delete()

    code = "".join(str(random.randint(0, 9)) for _ in range(LINK_CODE_LENGTH))
    await LinkCode(code=code, telegram_user_id=telegram_user_id).insert()

    return code


async def confirm_link(code: str, whatsapp_phone: str) -> bool:
    """Confirm link using one-time code. Returns True on success."""
    record = await LinkCode.find_one(LinkCode.code == code)
    if not record:
        return False

    created_at = record.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
    if elapsed > LINK_CODE_TTL_SECONDS:
        await record.delete()
        return False

    telegram_user_id = record.telegram_user_id
    await record.delete()

    # Remove existing links for both sides (1:1 constraint)
    await AccountLink.find(AccountLink.telegram_user_id == telegram_user_id).delete()
    await AccountLink.find(AccountLink.whatsapp_phone == whatsapp_phone).delete()

    await AccountLink(
        telegram_user_id=telegram_user_id,
        whatsapp_phone=whatsapp_phone,
    ).insert()

    logger.info("Linked Telegram %s <-> WhatsApp %s", telegram_user_id, whatsapp_phone)
    return True


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
