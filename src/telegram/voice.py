"""Telegram voice message handler."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src import const
from src.alerts import check_and_send_alerts
from src.categorization import categorize_note
from src.config import settings
from src.credits import (
    calculate_token_cost,
    can_perform_operation,
    deduct_credits,
    get_user_tier,
    has_unlimited_voice_access,
    increment_transcription_stats,
    increment_user_stats,
    is_blocked_user,
    record_groq_usage,
    record_user_usage,
)
from src.dto import UserTier
from src.localization import translates
from src.mongo import (
    get_auto_categorize,
    get_auto_cleanup,
    get_chat_language,
    get_github_settings,
    get_gpt_command,
    get_preferred_provider,
)
from src.obsidian import save_transcription_to_obsidian
from src.telegram.bot import send_response
from src.telegram.chat_params import get_chat_id
from src.transcript_cleanup import cleanup_transcript
from src.transcription.service import transcribe_audio
from src.wit_tracking import increment_wit_usage, is_wit_available

logger = logging.getLogger(__name__)


def _select_provider(
    tier: UserTier,
    wit_available: bool,
    preferred_provider: str | None = None,
) -> str | None:
    """
    Select transcription provider based on user tier, availability, and preference.

    Default for all tiers: Wit.ai. Paid tiers can override via preferred_provider.
    Free/Blocked: preference ignored, auto-selection only.

    Returns:
        const.PROVIDER_GROQ, const.PROVIDER_WIT, or None if no provider available
    """
    groq_available = bool(settings.groq_api_key)

    # Free tier: Wit only, no Groq fallback, ignore preference
    if tier == UserTier.FREE:
        return const.PROVIDER_WIT if wit_available else None

    # Paid tiers with explicit preference
    if preferred_provider == const.PROVIDER_GROQ and groq_available:
        return const.PROVIDER_GROQ

    if preferred_provider == const.PROVIDER_WIT and wit_available:
        return const.PROVIDER_WIT

    # Auto or fallback: Wit primary, Groq secondary
    if wit_available:
        return const.PROVIDER_WIT
    return const.PROVIDER_GROQ if groq_available else None


async def _handle_obsidian_save(chat_id: str, text: str, language: str, user_id: str | None = None):
    """Save transcription to Obsidian and auto-categorize if enabled."""
    settings_chat_id = f"u_{user_id}" if chat_id.startswith("g_") and user_id else None
    saved, filename = await save_transcription_to_obsidian(
        chat_id,
        text,
        const.SOURCE_TELEGRAM,
        language,
        settings_chat_id=settings_chat_id,
    )
    lookup_id = settings_chat_id or chat_id
    if not (saved and filename and await get_auto_categorize(lookup_id)):
        return
    github_settings = await get_github_settings(lookup_id)
    if github_settings:
        await categorize_note(
            token=github_settings["token"],
            owner=github_settings["owner"],
            repo=github_settings["repo"],
            filename=filename,
            content=text,
        )


def _build_voice_response(text: str, gpt_command: str, message_id: int) -> dict:
    """Build response kwargs for voice transcription."""
    if text.lower().startswith(gpt_command):
        return {
            "response": f"Command \\*{gpt_command}* detected in the voice message."
            f"\nAsk GPT for: {text[len(gpt_command) :]}"
        }
    return {"response": text, "reply_to_message_id": message_id}


async def from_voice_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice/audio message from Telegram."""
    voice = update.message.voice or update.message.audio
    if not voice:
        return

    # Diagnostic logging for forwarded messages
    logger.debug(
        "MSG: voice=%s, audio=%s, user=%s, forward_origin=%s",
        bool(update.message.voice),
        bool(update.message.audio),
        update.effective_user.id if update.effective_user else None,
        update.message.forward_origin,
    )

    # Guard: channel forwards may not have effective_user
    if not update.effective_user:
        logger.debug("No effective_user, skipping (likely channel forward)")
        return

    user_id = str(update.effective_user.id)
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    # 1. Blocked check — FIRST
    if await is_blocked_user(user_id):
        await send_response(
            update,
            context,
            response=translates["blocked_message"].get(
                language, translates["blocked_message"]["en"]
            ),
        )
        return

    # 2. Tier + provider selection
    tier = await get_user_tier(user_id)
    wit_available = await is_wit_available()
    preferred = await get_preferred_provider(chat_id)
    provider = _select_provider(tier, wit_available, preferred)

    if provider is None:
        await send_response(
            update,
            context,
            response=translates["service_unavailable"].get(
                language, translates["service_unavailable"]["en"]
            ),
        )
        return

    # 3. Pre-check: has at least 1 token?
    if not await has_unlimited_voice_access(user_id):
        ok, _msg = await can_perform_operation(user_id, 1)
        if not ok:
            await send_response(
                update,
                context,
                response=translates["insufficient_credits"].get(
                    language, translates["insufficient_credits"]["en"]
                ),
            )
            return

    # 4. Transcription
    voice_file = await voice.get_file()
    file_data = await voice_file.download_as_bytearray()

    text, duration, wit_requests = await transcribe_audio(
        bytes(file_data), audio_format="ogg", language=language, provider=provider
    )

    logger.debug("Voice message translation: %s", text)
    if not text:
        logger.debug("Empty voice message.")
        return

    # 5. Calculate cost and deduct
    token_cost = calculate_token_cost(duration)
    if not await has_unlimited_voice_access(user_id):
        result = await deduct_credits(user_id, token_cost)
        await record_user_usage(
            user_id, duration, token_cost, result.free_used, result.purchased_used
        )

        if result.overdraft:
            await send_response(
                update,
                context,
                response=translates["credits_exhausted_warning"].get(
                    language, translates["credits_exhausted_warning"]["en"]
                ),
            )

    # 6. Track provider usage
    if provider == const.PROVIDER_WIT:
        await increment_wit_usage(wit_requests)
        await check_and_send_alerts(context.bot)
    elif provider == const.PROVIDER_GROQ:
        await record_groq_usage(duration)

    await increment_transcription_stats()
    await increment_user_stats(user_id, audio_seconds=duration)

    # 7. Optional transcript cleanup
    settings_chat_id = f"u_{user_id}" if chat_id.startswith("g_") and user_id else chat_id
    if text and await get_auto_cleanup(settings_chat_id) and tier != UserTier.FREE:
        text = await cleanup_transcript(text)

    # 8. Obsidian integration
    await _handle_obsidian_save(chat_id, text, language, user_id=user_id)

    # 9. Send response
    gpt_command = await get_gpt_command(chat_id)
    response_kwargs = _build_voice_response(text, gpt_command, update.message.message_id)
    await send_response(update, context, **response_kwargs)
