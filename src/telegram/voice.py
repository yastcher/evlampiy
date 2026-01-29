"""Telegram voice message handler."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src import const
from src.alerts import check_and_send_alerts
from src.chat_params import get_chat_id
from src.config import settings
from src.credits import (
    can_perform_operation,
    deduct_credits,
    get_user_tier,
    grant_initial_credits_if_eligible,
    has_unlimited_access,
    increment_transcription_stats,
    increment_user_stats,
    record_groq_usage,
)
from src.dto import UserTier
from src.localization import translates
from src.mongo import get_chat_language, get_gpt_command
from src.obsidian import save_transcription_to_obsidian
from src.telegram.bot import send_response
from src.transcription.service import transcribe_audio
from src.wit_tracking import increment_wit_usage, is_wit_available

logger = logging.getLogger(__name__)


def _select_provider(tier: UserTier, wit_available: bool) -> str | None:
    """
    Select transcription provider based on user tier and Wit.ai availability.

    VIP and ADMIN users get Groq (if configured) else Wit.
    Returns:
        const.PROVIDER_GROQ, const.PROVIDER_WIT, or None if no provider available
    """
    if tier == UserTier.VIP:
        return const.PROVIDER_GROQ if settings.groq_api_key else const.PROVIDER_WIT

    if wit_available:
        return const.PROVIDER_WIT

    if tier == UserTier.PAID and settings.groq_api_key:
        return const.PROVIDER_GROQ

    return None


async def from_voice_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice message from Telegram."""
    if not update.message.voice:
        return

    user_id = update.effective_user.id
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    await grant_initial_credits_if_eligible(user_id)

    tier = await get_user_tier(user_id)
    wit_available = await is_wit_available()
    provider = _select_provider(tier, wit_available)

    if provider is None:
        await send_response(
            update, context, response=translates["service_unavailable"].get(language, translates["service_unavailable"]["en"])
        )
        return

    if not has_unlimited_access(user_id):
        ok, msg = await can_perform_operation(user_id, settings.credit_cost_voice)
        if not ok:
            await send_response(
                update, context, response=translates["insufficient_credits"].get(language, translates["insufficient_credits"]["en"])
            )
            return

    voice_file = await update.message.voice.get_file()
    file_data = await voice_file.download_as_bytearray()

    use_groq = provider == const.PROVIDER_GROQ
    text, duration = await transcribe_audio(
        bytes(file_data), audio_format="ogg", language=language, use_groq=use_groq
    )

    logger.debug("Voice message translation: %s", text)
    if not text:
        logger.debug("Empty voice message.")
        return

    if not has_unlimited_access(user_id):
        await deduct_credits(user_id, settings.credit_cost_voice)

    if provider == const.PROVIDER_WIT:
        await increment_wit_usage()
        await check_and_send_alerts(context.bot)
    elif provider == const.PROVIDER_GROQ:
        await record_groq_usage(duration)

    await increment_transcription_stats()
    await increment_user_stats(user_id, audio_seconds=duration)
    await save_transcription_to_obsidian(chat_id, text, const.SOURCE_TELEGRAM, language)

    gpt_command = await get_gpt_command(chat_id)
    if text.lower().startswith(gpt_command):
        response_kwargs = {
            "response": f"Command \\*{gpt_command}* detected in the voice message."
            f"\nAsk GPT for: {text[len(gpt_command) :]}"
        }
    else:
        response_kwargs = {
            "response": text,
            "reply_to_message_id": update.message.message_id,
        }

    await send_response(update, context, **response_kwargs)
