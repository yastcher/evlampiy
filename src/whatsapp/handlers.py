"""WhatsApp message handlers."""

import logging

import httpx
from pywa.types import Message
from pywa_async import WhatsApp

from src import const
from src.account_linking import confirm_link, get_linked_telegram_id
from src.config import settings
from src.credits import get_user_tier
from src.dto import UserTier
from src.mongo import (
    get_chat_language,
)
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


async def handle_link_command(wa: WhatsApp, message: Message) -> None:
    """Handle account linking command from WhatsApp."""
    phone = message.from_user.wa_id
    text = message.text or ""
    parts = text.strip().split(maxsplit=1)
    code = parts[1] if len(parts) > 1 else ""

    if not code:
        await wa.send_message(to=phone, text="Usage: link <code>")
        return

    result = await confirm_link(code, phone)
    if result == "success":
        await wa.send_message(to=phone, text="Account linked successfully!")
    elif result == "rate_limited":
        await wa.send_message(
            to=phone,
            text="Too many attempts. Please wait 5 minutes and try again.",
        )
    else:
        await wa.send_message(
            to=phone,
            text="Invalid or expired code. Try /link_whatsapp in Telegram.",
        )


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
