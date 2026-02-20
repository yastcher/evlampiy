"""Optional LLM-based cleanup of raw voice transcriptions."""

import logging

from src.ai_client import cleanup_text

logger = logging.getLogger(__name__)

_CLEANUP_PROMPT_BASE = (
    "Clean up this voice transcription. Your primary goal is to capture the speaker's "
    "intent — NOT to rephrase or rewrite their words.\n\n"
    "Rules:\n"
    "1. Remove filler words and false starts (ну, то есть, аа, эм, like, you know, etc.).\n"
    "2. Fix obvious transcription errors (misheard words, garbled phrases). "
    "If unsure what a garbled word means, leave it as-is.\n"
    "3. Do NOT rephrase, restructure, or add information.\n"
    "4. Preserve the original language. Fix punctuation minimally.\n"
    "5. If two fragments were concatenated without a break, split into sentences.\n"
    "Return only the cleaned text, nothing else.\n"
)

_MIN_TEXT_LENGTH = 20
_MIN_TOKENS = 200
_MAX_TOKENS = 4096


def _build_cleanup_prompt(
    text: str,
    vocabulary: dict | None,
    context: list[str] | None,
) -> str:
    parts = [_CLEANUP_PROMPT_BASE]
    if context:
        context_notes = "\n---\n".join(context)
        parts.append(
            f"\nContext from recent notes in this chat "
            f"(use to understand garbled words):\n{context_notes}\n"
        )
    if vocabulary:
        flat_keywords = ", ".join(kw for keywords in vocabulary.values() for kw in keywords)
        parts.append(
            f"\nDomain vocabulary (may appear garbled in transcription): {flat_keywords}\n"
        )
    parts.append(f"\nTranscription:\n{text}")
    return "".join(parts)


async def cleanup_transcript(
    text: str,
    vocabulary: dict | None = None,
    context: list[str] | None = None,
) -> str:
    """Clean up raw transcription using LLM. Returns original text on failure."""
    if len(text) < _MIN_TEXT_LENGTH:
        return text

    prompt = _build_cleanup_prompt(text, vocabulary, context)
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
