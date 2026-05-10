"""WhatsApp message handlers."""

import logging

import httpx
from pywa.types import Message
from pywa_async import WhatsApp

from src import const
from src.account_linking import get_linked_telegram_id
from src.config import settings
from src.credits import get_user_tier
from src.dto import UserTier
from src.mongo import (
    get_chat_language,
)
from src.services.account_linking_service import LinkOutcome, process_link_command
from src.services.voice_pipeline import process_voice
from src.whatsapp.client import WHATSAPP_CHAT_PREFIX

logger = logging.getLogger(__name__)


def register_handlers(wa: WhatsApp) -> None:
    """Register WhatsApp message handlers."""

    @wa.on_message()  # ty: ignore[invalid-argument-type, missing-argument]
    async def handle_message(client: WhatsApp, message: Message) -> None:
        """Handle incoming WhatsApp messages."""
        if message.text and message.text.strip().lower().startswith("link "):
            await handle_link_command(client, message)
        elif message.audio or message.voice:
            await handle_voice_message(client, message)


_LINK_REPLIES: dict[LinkOutcome, str] = {
    LinkOutcome.USAGE: "Usage: link <code>",
    LinkOutcome.SUCCESS: "Account linked successfully!",
    LinkOutcome.RATE_LIMITED: "Too many attempts. Please wait 5 minutes and try again.",
    LinkOutcome.INVALID: "Invalid or expired code. Try /link_whatsapp in Telegram.",
}


async def handle_link_command(wa: WhatsApp, message: Message) -> None:
    """Handle account linking command from WhatsApp — thin adapter."""
    phone = message.from_user.wa_id
    outcome = await process_link_command(message.text or "", phone)
    await wa.send_message(to=phone, text=_LINK_REPLIES[outcome])


async def handle_voice_message(wa: WhatsApp, message: Message) -> None:
    """Handle voice message from WhatsApp — thin adapter over `voice_pipeline`."""
    phone_number = message.from_user.wa_id
    chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"

    audio = message.voice or message.audio
    if not audio:
        return

    language = await get_chat_language(chat_id)

    try:
        media_url = await wa.get_media_url(audio.id)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                media_url,  # ty: ignore[invalid-argument-type]
                headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
            )
            response.raise_for_status()
            audio_bytes = response.content
    except Exception as e:
        logger.error("Failed to download WhatsApp audio: %s", e)
        return

    telegram_user_id = await get_linked_telegram_id(phone_number)
    tier = await get_user_tier(telegram_user_id) if telegram_user_id else UserTier.FREE

    result = await process_voice(
        audio_bytes=audio_bytes,
        audio_format="ogg",
        source=const.SOURCE_WHATSAPP,
        chat_id=chat_id,
        language=language,
        tier=tier,
    )
    if result is None:
        logger.debug("Empty WhatsApp voice message from %s", phone_number)
        return

    await wa.send_message(to=phone_number, text=result.text)
    logger.info("Sent transcription to WhatsApp user %s", phone_number)
