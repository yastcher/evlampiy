"""Groq Whisper client for speech-to-text."""

import logging
from io import BytesIO

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_TIMEOUT = 30.0

LANGUAGE_MAP = {"en": "en", "ru": "ru", "es": "es", "de": "de"}


async def transcribe_with_groq(
    audio_bytes: bytes,
    language: str,
    audio_format: str = "ogg",
) -> str:
    """
    Transcribe audio using Groq Whisper API.

    Args:
        audio_bytes: Raw audio data
        language: ISO language code (en, ru, es, de)
        audio_format: Audio format for filename hint

    Returns:
        Transcribed text or empty string on error
    """
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY not configured")
        return ""

    groq_language = LANGUAGE_MAP.get(language, "en")

    files = {
        "file": (f"audio.{audio_format}", BytesIO(audio_bytes), f"audio/{audio_format}"),
        "model": (None, settings.groq_model),
        "language": (None, groq_language),
        "response_format": (None, "text"),
    }

    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=GROQ_TIMEOUT) as client:
            response = await client.post(
                GROQ_API_URL,
                files=files,
                headers=headers,
            )
            response.raise_for_status()
            return response.text.strip()
    except httpx.HTTPStatusError as e:
        logger.error("Groq API error: %s - %s", e.response.status_code, e.response.text)
        return ""
    except httpx.RequestError as e:
        logger.error("Groq request failed: %s", e)
        return ""
