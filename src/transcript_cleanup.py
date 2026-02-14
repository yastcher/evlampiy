"""Optional LLM-based cleanup of raw voice transcriptions."""

import logging

from src.ai_client import cleanup_text

logger = logging.getLogger(__name__)

_CLEANUP_PROMPT = (
    "Clean up this voice transcription. Remove filler words, false starts, "
    "and repetitions. Fix punctuation and capitalization. Preserve the original "
    "meaning, language, and style. Do not add new information. Do not translate. "
    "Return only the cleaned text, nothing else.\n\n"
    "Transcription:\n{text}"
)

_MIN_TEXT_LENGTH = 20
_MIN_TOKENS = 200
_MAX_TOKENS = 4096


async def cleanup_transcript(text: str) -> str:
    """Clean up raw transcription using LLM. Returns original text on failure."""
    if len(text) < _MIN_TEXT_LENGTH:
        return text

    prompt = _CLEANUP_PROMPT.format(text=text)
    max_tokens = max(_MIN_TOKENS, min(_MAX_TOKENS, len(text) // 2 + 200))

    try:
        result = await cleanup_text(prompt, max_tokens)
    except Exception:
        logger.exception("Transcript cleanup failed, text_length=%d", len(text))
        return text

    if not result or not result.strip():
        logger.warning("Transcript cleanup returned empty, text_length=%d", len(text))
        return text

    logger.debug(
        "Transcript cleaned, original_length=%d, cleaned_length=%d", len(text), len(result)
    )
    return result
