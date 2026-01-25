"""WhatsApp client initialization."""

from pywa import WhatsApp

from src.config import settings

WHATSAPP_CHAT_PREFIX = "wa_"

# Lazy initialization - only create client if configured
_wa_client: WhatsApp | None = None


def get_whatsapp_client() -> WhatsApp | None:
    """Get WhatsApp client instance (lazy initialization)."""
    global _wa_client

    if not settings.whatsapp_token or not settings.whatsapp_phone_id:
        return None

    if _wa_client is None:
        _wa_client = WhatsApp(
            phone_id=settings.whatsapp_phone_id,
            token=settings.whatsapp_token,
            app_id=int(settings.whatsapp_app_id) if settings.whatsapp_app_id else None,
            app_secret=settings.whatsapp_app_secret or None,
            verify_token=settings.whatsapp_verify_token or None,
        )

    return _wa_client
