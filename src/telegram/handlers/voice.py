"""Telegram voice message handler — thin adapter over `src.services.voice_pipeline`."""

import io
import logging
import typing

from aiogram import Bot
from aiogram.types import Audio, Message, Voice

from src import const
from src.alerts import check_and_send_alerts
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
from src.mongo import get_chat_language, get_gpt_command, get_preferred_provider
from src.services.voice_pipeline import process_voice
from src.telegram.bot import send_response
from src.telegram.chat_params import get_chat_id
from src.types import ChatId, Language, UserId
from src.wit_tracking import increment_wit_usage, is_wit_available

logger = logging.getLogger(__name__)


def _select_provider(
    tier: UserTier,
    wit_available: bool,
    preferred_provider: str | None = None,
) -> str | None:
    """Select transcription provider based on user tier, availability, and preference.

    Default for all tiers: Wit.ai. Paid tiers can override via preferred_provider.
    Free/Blocked: preference ignored, auto-selection only.
    Returns the provider name or ``None`` if no provider is available.
    """
    groq_available = bool(settings.groq_api_key)

    if tier == UserTier.FREE:
        return const.PROVIDER_WIT if wit_available else None

    if preferred_provider == const.PROVIDER_GROQ and groq_available:
        return const.PROVIDER_GROQ

    if preferred_provider == const.PROVIDER_WIT and wit_available:
        return const.PROVIDER_WIT

    if wit_available:
        return const.PROVIDER_WIT
    return const.PROVIDER_GROQ if groq_available else None


def _build_voice_response(text: str, gpt_command: str, message_id: int) -> dict[str, typing.Any]:
    """Build response kwargs: GPT-command-prefixed messages get a dedicated label."""
    if text.lower().startswith(gpt_command):
        return {
            "response": f"Command \\*{gpt_command}* detected in the voice message."
            f"\nAsk GPT for: {text[len(gpt_command) :]}"
        }
    return {"response": text, "reply_to_message_id": message_id}


class _VoiceContext(typing.NamedTuple):
    """Validated context for voice message processing."""

    voice: Voice | Audio
    user_id: UserId
    chat_id: ChatId
    language: Language
    provider: str
    tier: UserTier
    message_id: int


async def _validate_voice_input(message: Message, bot: Bot) -> _VoiceContext | None:
    """Validate voice input and resolve user context. Sends error message on failure."""
    voice: Voice | Audio | None = message.voice or message.audio
    if not voice:
        return None

    logger.debug(
        "MSG: voice=%s, audio=%s, user=%s, forward_origin=%s",
        bool(message.voice),
        bool(message.audio),
        message.from_user.id if message.from_user else None,
        message.forward_origin,
    )

    if not message.from_user:
        logger.debug("No effective_user, skipping (likely channel forward)")
        return None

    user_id = str(message.from_user.id)
    chat_id = get_chat_id(message)
    language = await get_chat_language(chat_id)

    if await is_blocked_user(user_id):
        await send_response(
            message,
            bot,
            response=translates["blocked_message"].get(
                language, translates["blocked_message"]["en"]
            ),
        )
        return None

    tier = await get_user_tier(user_id)
    wit_available = await is_wit_available(language)
    preferred = await get_preferred_provider(chat_id)
    provider = _select_provider(tier, wit_available, preferred)

    if provider is None:
        await send_response(
            message,
            bot,
            response=translates["service_unavailable"].get(
                language, translates["service_unavailable"]["en"]
            ),
        )
        return None

    if not await has_unlimited_voice_access(user_id):
        ok, _msg = await can_perform_operation(user_id, 1)
        if not ok:
            await send_response(
                message,
                bot,
                response=translates["insufficient_credits"].get(
                    language, translates["insufficient_credits"]["en"]
                ),
            )
            return None

    return _VoiceContext(voice, user_id, chat_id, language, provider, tier, message.message_id)


async def _download_voice(bot: Bot, voice: Voice | Audio) -> bytes:
    """Download voice/audio file content from Telegram."""
    buf = io.BytesIO()
    await bot.download(voice, destination=buf)
    return buf.getvalue()


async def from_voice_to_text(message: Message, bot: Bot) -> None:
    """Handle incoming voice/audio message from Telegram."""
    ctx = await _validate_voice_input(message, bot)
    if not ctx:
        return

    file_data = await _download_voice(bot, ctx.voice)

    settings_chat_id = f"u_{ctx.user_id}" if ctx.chat_id.startswith("g_") and ctx.user_id else None
    result = await process_voice(
        audio_bytes=file_data,
        audio_format="ogg",
        source=const.SOURCE_TELEGRAM,
        chat_id=ctx.chat_id,
        language=ctx.language,
        provider=ctx.provider,
        tier=ctx.tier,
        settings_chat_id=settings_chat_id,
    )
    if result is None:
        return

    token_cost = calculate_token_cost(result.duration)
    if not await has_unlimited_voice_access(ctx.user_id):
        deduct_result = await deduct_credits(ctx.user_id, token_cost)
        await record_user_usage(
            ctx.user_id,
            result.duration,
            token_cost,
            deduct_result.free_used,
            deduct_result.purchased_used,
        )
        if deduct_result.overdraft:
            await send_response(
                message,
                bot,
                response=translates["credits_exhausted_warning"].get(
                    ctx.language, translates["credits_exhausted_warning"]["en"]
                ),
            )

    if ctx.provider == const.PROVIDER_WIT:
        await increment_wit_usage(result.wit_requests, language=ctx.language)
        await check_and_send_alerts(bot)
    elif ctx.provider == const.PROVIDER_GROQ:
        await record_groq_usage(result.duration)

    await increment_transcription_stats()
    await increment_user_stats(ctx.user_id, audio_seconds=result.duration)

    gpt_command = await get_gpt_command(ctx.chat_id)
    response_kwargs = _build_voice_response(result.text, gpt_command, ctx.message_id)
    await send_response(message, bot, **response_kwargs)
