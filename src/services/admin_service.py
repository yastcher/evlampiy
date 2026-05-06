"""Admin use-case service: user-id parsing + role/credits operations."""

import logging
from collections.abc import Sequence

from src import const
from src.credits import admin_add_credits
from src.mongo import add_user_role, remove_user_role
from src.types import UserId

logger = logging.getLogger(__name__)


def parse_user_id(args: Sequence[str]) -> UserId | None:
    """Extract and validate user_id from command args. Numeric strings only."""
    if not args:
        return None
    user_id = args[0].strip()
    if not user_id.isdigit():
        return None
    return user_id


async def assign_role(user_id: UserId, role: str, admin_id: str) -> None:
    """Add a role to a user (VIP/tester)."""
    await add_user_role(user_id, role, admin_id)


async def revoke_role(user_id: UserId, role: str) -> bool:
    """Remove a role from a user. Returns True if the role was actually removed."""
    return await remove_user_role(user_id, role)


async def block_user(user_id: UserId, admin_id: str, reason: str = "") -> None:
    """Mark a user as blocked. ``reason`` is logged for audit."""
    await add_user_role(user_id, const.ROLE_BLOCKED, admin_id)
    if reason:
        logger.info("User %s blocked by %s. Reason: %s", user_id, admin_id, reason)
    else:
        logger.info("User %s blocked by %s", user_id, admin_id)


async def unblock_user(user_id: UserId) -> bool:
    """Lift the block on a user. Returns True if the block was actually removed."""
    return await remove_user_role(user_id, const.ROLE_BLOCKED)


def parse_credits_amount(raw: str) -> int | None:
    """Parse a positive integer credits amount from a CLI arg. None on invalid input."""
    try:
        amount = int(raw)
    except ValueError:
        return None
    return amount if amount > 0 else None


async def change_credits(user_id: UserId, amount: int) -> int:
    """Add credits to a user. Returns the new total balance."""
    return await admin_add_credits(user_id, amount)
