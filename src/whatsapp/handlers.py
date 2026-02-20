"""WhatsApp message handlers."""

import asyncio
import logging

import httpx
from pywa import WhatsApp
from pywa.types import Message

from src import const
from src.account_linking import confirm_link, get_linked_telegram_id
from src.categorization import categorize_note
from src.config import settings
from src.credits import get_user_tier
from src.dto import UserTier
from src.mongo import get_auto_categorize, get_auto_cleanup, get_chat_language, get_github_settings
from src.obsidian import save_transcription_to_obsidian
from src.transcript_cleanup import cleanup_transcript
from src.transcription.service import transcribe_audio
from src.whatsapp.client import WHATSAPP_CHAT_PREFIX

logger = logging.getLogger(__name__)


def register_handlers(wa: WhatsApp) -> None:
    """Register WhatsApp message handlers."""

    @wa.on_message()
    async def handle_message(client: WhatsApp, message: Message):
        """Handle incoming WhatsApp messages."""
        if message.text and message.text.strip().lower().startswith("link "):
            await handle_link_command(client, message)
        elif message.audio or message.voice:
            await handle_voice_message(client, message)


async def handle_link_command(wa: WhatsApp, message: Message) -> None:
    """Handle account linking command from WhatsApp."""
    phone = message.from_user.wa_id
    parts = message.text.strip().split(maxsplit=1)
    code = parts[1] if len(parts) > 1 else ""

    if not code:
        await asyncio.to_thread(wa.send_message, to=phone, text="Usage: link <code>")
        return

    result = await confirm_link(code, phone)
    if result == "success":
        await asyncio.to_thread(wa.send_message, to=phone, text="Account linked successfully!")
    elif result == "rate_limited":
        await asyncio.to_thread(
            wa.send_message,
            to=phone,
            text="Too many attempts. Please wait 5 minutes and try again.",
        )
    else:
        await asyncio.to_thread(
            wa.send_message,
            to=phone,
            text="Invalid or expired code. Try /link_whatsapp in Telegram.",
        )


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
    text, _, _ = await transcribe_audio(audio_bytes, audio_format="ogg", language=language)

    if not text:
        logger.debug("Empty WhatsApp voice message from %s", phone_number)
        return

    # Optional transcript cleanup (only for linked paid users)
    telegram_user_id = await get_linked_telegram_id(phone_number)
    if telegram_user_id and await get_auto_cleanup(chat_id):
        tier = await get_user_tier(telegram_user_id)
        if tier != UserTier.FREE:
            text = await cleanup_transcript(text)

    saved, filename = await save_transcription_to_obsidian(
        chat_id,
        text,
        const.SOURCE_WHATSAPP,
        language,
    )
    if saved and filename and await get_auto_categorize(chat_id):
        github_settings = await get_github_settings(chat_id)
        if github_settings:
            await categorize_note(
                token=github_settings["token"],
                owner=github_settings["owner"],
                repo=github_settings["repo"],
                filename=filename,
                content=text,
            )

    # Send transcription back
    await asyncio.to_thread(wa.send_message, to=phone_number, text=text)
    logger.info("Sent transcription to WhatsApp user %s", phone_number)
