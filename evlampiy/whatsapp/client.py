"""WhatsApp client initialization."""

import enum
import logging

from fastapi import FastAPI
from pywa_async import WhatsApp

from evlampiy.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_CHAT_PREFIX = "wa_"


class WhatsAppState(enum.StrEnum):
    """Whether the WhatsApp webhook is served; /health reports it."""

    OFF = "off"
    ON = "on"
    # Configured, but without the app secret pywa would stop checking signatures.
    REFUSED = "no app secret"


class _WhatsAppClientHolder:
    """Module-level singleton container for the WhatsApp client."""

    instance: WhatsApp | None = None


def whatsapp_state() -> WhatsAppState:
    if not settings.whatsapp_token or not settings.whatsapp_phone_id:
        return WhatsAppState.OFF
    if not settings.whatsapp_app_secret:
        return WhatsAppState.REFUSED
    return WhatsAppState.ON


def init_whatsapp_client(server: FastAPI) -> WhatsApp | None:
    """Create the WhatsApp client bound to a FastAPI server.

    pywa registers webhook routes on the server during construction, so the
    server must exist before the client. Returns None unless WhatsApp is fully
    configured: without the app secret pywa would accept unsigned, forgeable
    updates, so the webhook stays off and the log says why.
    """
    state = whatsapp_state()
    if state is WhatsAppState.REFUSED:
        logger.error(
            "WhatsApp is configured without WHATSAPP_APP_SECRET: the webhook stays off, "
            "since pywa would accept unsigned updates"
        )
    if state is not WhatsAppState.ON:
        return None

    if _WhatsAppClientHolder.instance is None:
        _WhatsAppClientHolder.instance = WhatsApp(
            phone_id=settings.whatsapp_phone_id,
            token=settings.whatsapp_token,
            server=server,
            app_id=int(settings.whatsapp_app_id) if settings.whatsapp_app_id else None,
            app_secret=settings.whatsapp_app_secret,
            verify_token=settings.whatsapp_verify_token or None,
        )

    return _WhatsAppClientHolder.instance
