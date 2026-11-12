"""Telegram voice message handler — thin adapter over `evlampiy.services.voice_pipeline`."""

import io
import logging
import typing

from aiogram import Bot
from aiogram.types import Audio, Message, Voice

from evlampiy import const
from evlampiy.alerts import check_wit_alerts
from evlampiy.dto import UserTier
from evlampiy.localization import translates
from evlampiy.mongo import get_chat_language, get_gpt_command, get_preferred_provider
from evlampiy.services.voice_access import Refusal, admit_voice, settle_voice
from evlampiy.services.voice_pipeline import process_voice
from evlampiy.telegram.bot import send_response
from evlampiy.telegram.chat_params import get_chat_id
from evlampiy.types import ChatId, Language, UserId

logger = logging.getLogger(__name__)


def _build_voice_response(text: str, gpt_command: str, message_id: int) -> dict[str, typing.Any]:
    """Build response kwargs: GPT-command-prefixed messages get a dedicated label."""
    if text.lower().startswith(gpt_command):
        return {
            "response": f"Command \\*{gpt_command}* detected in the voice message."
            f"\nAsk GPT for: {text[len(gpt_command) :]}"
        }
    return {"response": text, "reply_to_message_id": message_id}


# What the user is told when `admit_voice` refuses, as keys of `translates`.
_REFUSAL_REPLIES: dict[Refusal, str] = {
    Refusal.BLOCKED: "blocked_message",
    Refusal.NO_PROVIDER: "service_unavailable",
    Refusal.NO_TOKENS: "insufficient_credits",
}


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

    admission = await admit_voice(user_id, language, await get_preferred_provider(chat_id))
    if isinstance(admission, Refusal):
        key = _REFUSAL_REPLIES[admission]
        await send_response(message, bot, response=translates[key].get(language, translates[key]["en"]))
        return None

    return _VoiceContext(voice, user_id, chat_id, language, admission.provider, admission.tier, message.message_id)


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

    overdraft = await settle_voice(ctx.user_id, ctx.provider, ctx.language, result.duration, result.wit_requests)
    if overdraft:
        await send_response(
            message,
            bot,
            response=translates["credits_exhausted_warning"].get(
                ctx.language, translates["credits_exhausted_warning"]["en"]
            ),
        )
    if ctx.provider == const.PROVIDER_WIT:
        await check_wit_alerts()

    gpt_command = await get_gpt_command(ctx.chat_id)
    response_kwargs = _build_voice_response(result.text, gpt_command, ctx.message_id)
    await send_response(message, bot, **response_kwargs)
