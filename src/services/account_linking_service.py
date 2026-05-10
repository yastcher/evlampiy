"""Account-linking use case (WhatsApp ↔ Telegram). Framework-agnostic."""

import enum

from src.account_linking import confirm_link


class LinkOutcome(enum.StrEnum):
    """Outcome of an inbound `link <code>` command from WhatsApp."""

    USAGE = "usage"
    SUCCESS = "success"
    RATE_LIMITED = "rate_limited"
    INVALID = "invalid"


async def process_link_command(text: str, phone: str) -> LinkOutcome:
    """Parse ``link <code>`` text and apply the link. Adapter renders the reply."""
    parts = text.strip().split(maxsplit=1)
    code = parts[1] if len(parts) > 1 else ""
    if not code:
        return LinkOutcome.USAGE
    result = await confirm_link(code, phone)
    if result == "success":
        return LinkOutcome.SUCCESS
    if result == "rate_limited":
        return LinkOutcome.RATE_LIMITED
    return LinkOutcome.INVALID
