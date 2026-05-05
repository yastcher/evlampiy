"""Voice processing pipeline: framework-agnostic core for transcription handlers.

Used by both `src/telegram/voice.py` and `src/whatsapp/handlers.py::handle_voice_message`.
Does not import aiogram or pywa — receives already-downloaded `audio_bytes`.
"""

import dataclasses
import logging

from src import const
from src.categorization import categorize_note
from src.dto import UserTier
from src.mongo import (
    get_auto_categorize,
    get_auto_cleanup,
    get_github_settings,
    get_recent_transcriptions,
    save_recent_transcription,
)
from src.obsidian import save_transcription_to_obsidian
from src.transcript_cleanup import cleanup_transcript
from src.transcription.service import transcribe_audio
from src.types import ChatId, Language

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class VoicePipelineResult:
    """Outcome of the voice pipeline. `None` means no reply should be sent."""

    text: str  # final reply text (raw or cleaned, depending on tier + auto_cleanup)
    duration: int  # seconds — caller uses this for credits/usage accounting
    wit_requests: int  # number of wit.ai requests — caller uses for usage tracking


async def process_voice(  # noqa: PLR0913 — single-purpose pipeline; bundling args into a DTO would only add ceremony
    *,
    audio_bytes: bytes,
    audio_format: str,
    source: str,
    chat_id: ChatId,
    language: Language,
    provider: str | None = None,
    tier: UserTier = UserTier.FREE,
    settings_chat_id: ChatId | None = None,
) -> VoicePipelineResult | None:
    """Run transcription → optional cleanup → Obsidian save → optional categorize.

    Returns ``None`` if transcription is empty (caller should skip reply).
    Cleanup runs only for non-FREE tiers (matches telegram + whatsapp legacy behavior).
    The user-facing text is the cleaned text only when ``auto_cleanup`` is on for the
    chat; otherwise the raw transcription is returned and Obsidian receives the cleaned
    version side-by-side via ``original_text``.
    """
    text, duration, wit_requests = await transcribe_audio(
        audio_bytes,
        audio_format=audio_format,
        language=language,
        provider=provider if provider is not None else const.PROVIDER_WIT,
    )
    logger.debug("Voice transcription (%s, %s): %s", source, provider, text)
    if not text:
        return None

    settings_id = settings_chat_id or chat_id
    raw_text = text
    obsidian_text = text
    if tier != UserTier.FREE:
        recent_context = await get_recent_transcriptions(settings_id)
        if await get_auto_cleanup(settings_id):
            text = await cleanup_transcript(raw_text, context=recent_context)
            obsidian_text = text
        else:
            obsidian_text = await cleanup_transcript(raw_text, context=recent_context)
        await save_recent_transcription(settings_id, obsidian_text)

    original_for_obsidian = raw_text if raw_text != obsidian_text else None
    saved, filename = await save_transcription_to_obsidian(
        chat_id,
        obsidian_text,
        source,
        language,
        settings_chat_id=settings_chat_id,
        original_text=original_for_obsidian,
    )
    if saved and filename and await get_auto_categorize(settings_id):
        repo_info = await get_github_settings(settings_id)
        if repo_info:
            await categorize_note(
                repo_info=repo_info,
                filename=filename,
                content=obsidian_text,
            )

    return VoicePipelineResult(text=text, duration=duration, wit_requests=wit_requests)
