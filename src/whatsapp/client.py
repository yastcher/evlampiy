"""WhatsApp client initialization."""

from fastapi import FastAPI
from pywa import WhatsApp

from src.config import settings

WHATSAPP_CHAT_PREFIX = "wa_"


class _WhatsAppClientHolder:
    """Module-level singleton container for the WhatsApp client."""

    instance: WhatsApp | None = None


def init_whatsapp_client(server: FastAPI) -> WhatsApp | None:
    """Create the WhatsApp client bound to a FastAPI server.

    pywa registers webhook routes on the server during construction, so the
    server must exist before the client. Returns None if WhatsApp credentials
    are not configured.
    """
    if not settings.whatsapp_token or not settings.whatsapp_phone_id:
        return None

    if _WhatsAppClientHolder.instance is None:
        _WhatsAppClientHolder.instance = WhatsApp(
            phone_id=settings.whatsapp_phone_id,
            token=settings.whatsapp_token,
            server=server,
            app_id=int(settings.whatsapp_app_id) if settings.whatsapp_app_id else None,
            app_secret=settings.whatsapp_app_secret or None,
            verify_token=settings.whatsapp_verify_token or None,
        )

    return _WhatsAppClientHolder.instance
