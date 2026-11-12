"""WhatsApp message handlers.

A number linked to a Telegram account acts as that user's private chat there (ADR-001):
the block, the tier, the tokens and the settings are the Telegram user's.
"""

import logging

import httpx
from pywa.types import Message
from pywa_async import WhatsApp

from evlampiy import const
from evlampiy.account_linking import get_linked_telegram_id
from evlampiy.alerts import check_wit_alerts
from evlampiy.config import settings
from evlampiy.localization import translates
from evlampiy.mongo import get_chat_language, get_preferred_provider
from evlampiy.services.account_linking_service import LinkOutcome, process_link_command
from evlampiy.services.voice_access import Refusal, admit_voice, settle_voice
from evlampiy.services.voice_pipeline import process_voice
from evlampiy.types import Language
from evlampiy.whatsapp.client import WHATSAPP_CHAT_PREFIX

logger = logging.getLogger(__name__)


def register_handlers(wa: WhatsApp) -> None:
    """Register WhatsApp message handlers."""

    @wa.on_message()
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

_USERNAME_ACCOUNT_REPLY = "Sorry, this bot doesn't support WhatsApp accounts with a username yet."

# What the user is told when `admit_voice` refuses, as keys of `translates`; WhatsApp sells
# nothing, so a missing token points to Telegram.
_REFUSAL_REPLIES: dict[Refusal, str] = {
    Refusal.BLOCKED: "blocked_message",
    Refusal.NO_PROVIDER: "service_unavailable",
    Refusal.NO_TOKENS: "whatsapp_insufficient_credits",
}


def _reply(key: str, language: Language) -> str:
    return translates[key].get(language, translates[key]["en"])


async def _refuse_username_account(wa: WhatsApp, message: Message) -> None:
    """Answer by BSUID a user whose WhatsApp username hides the phone number every WhatsApp user is keyed by."""
    logger.info("WhatsApp user %s has a username and no phone number", message.from_user.bsuid)
    await wa.send_message(to=message.from_user.bsuid, text=_USERNAME_ACCOUNT_REPLY)


async def handle_link_command(wa: WhatsApp, message: Message) -> None:
    """Handle account linking command from WhatsApp — thin adapter."""
    phone = message.from_user.wa_id
    if phone is None:
        await _refuse_username_account(wa, message)
        return
    outcome = await process_link_command(message.text or "", phone)
    await wa.send_message(to=phone, text=_LINK_REPLIES[outcome])


async def handle_voice_message(wa: WhatsApp, message: Message) -> None:
    """Handle voice message from WhatsApp — thin adapter over `voice_access` and `voice_pipeline`."""
    phone_number = message.from_user.wa_id
    if phone_number is None:
        await _refuse_username_account(wa, message)
        return

    audio = message.voice or message.audio
    if not audio:
        return
    chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"

    user_id = await get_linked_telegram_id(phone_number)
    if user_id is None:
        await wa.send_message(to=phone_number, text=_reply("whatsapp_link_required", await get_chat_language(chat_id)))
        return

    settings_chat_id = f"{const.CHAT_PREFIX_USER}{user_id}"
    language = await get_chat_language(settings_chat_id)
    admission = await admit_voice(user_id, language, await get_preferred_provider(settings_chat_id))
    if isinstance(admission, Refusal):
        await wa.send_message(to=phone_number, text=_reply(_REFUSAL_REPLIES[admission], language))
        return

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

    result = await process_voice(
        audio_bytes=audio_bytes,
        audio_format="ogg",
        source=const.SOURCE_WHATSAPP,
        chat_id=chat_id,
        language=language,
        provider=admission.provider,
        tier=admission.tier,
        settings_chat_id=settings_chat_id,
    )
    if result is None:
        logger.debug("Empty WhatsApp voice message from %s", phone_number)
        return

    overdraft = await settle_voice(user_id, admission.provider, language, result.duration, result.wit_requests)
    if admission.provider == const.PROVIDER_WIT:
        await check_wit_alerts()
    if overdraft:
        await wa.send_message(to=phone_number, text=_reply("whatsapp_credits_exhausted_warning", language))

    await wa.send_message(to=phone_number, text=result.text)
    logger.info("Sent transcription to WhatsApp user %s", phone_number)
