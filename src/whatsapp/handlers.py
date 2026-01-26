"""WhatsApp message handlers."""

import logging

import httpx
from pywa import WhatsApp
from pywa.types import Message

from src.config import settings
from src.mongo import get_chat_language
from src.obsidian import save_transcription_to_obsidian
from src.transcription.service import transcribe_audio
from src.whatsapp.client import WHATSAPP_CHAT_PREFIX

logger = logging.getLogger(__name__)


def register_handlers(wa: WhatsApp) -> None:
    """Register WhatsApp message handlers."""

    @wa.on_message()
    async def handle_message(client: WhatsApp, message: Message):
        """Handle incoming WhatsApp messages."""
        if message.audio or message.voice:
            await handle_voice_message(client, message)


async def handle_voice_message(wa: WhatsApp, message: Message) -> None:
    """Handle voice message from WhatsApp."""
    phone_number = message.from_user.wa_id
    chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"

    # Get audio from voice or audio message
    audio = message.voice or message.audio
    if not audio:
        return

    language = await get_chat_language(chat_id)

    # Download voice file from WhatsApp
    try:
        media_url = wa.get_media_url(audio.id)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
            )
            response.raise_for_status()
            audio_bytes = response.content
    except Exception as e:
        logger.error("Failed to download WhatsApp audio: %s", e)
        return

    # WhatsApp voice messages are opus in ogg container
    text = transcribe_audio(audio_bytes, audio_format="ogg", language=language)

    if not text:
        logger.debug("Empty WhatsApp voice message from %s", phone_number)
        return

    await save_transcription_to_obsidian(chat_id, text, "whatsapp", language)

    # Send transcription back
    wa.send_message(to=phone_number, text=text)
    logger.info("Sent transcription to WhatsApp user %s", phone_number)
