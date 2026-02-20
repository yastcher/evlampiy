"""Voice transcription service — platform-agnostic."""

import logging
from io import BytesIO

from pydub import AudioSegment

from src import const
from src.transcription.groq_client import transcribe_with_groq
from src.transcription.wit_client import voice_translators

logger = logging.getLogger(__name__)

CHUNK_LENGTH_MS = 19500  # Wit.ai limit: <20 sec
MS_PER_SECOND = 1000


def get_audio_duration_seconds(audio_bytes: bytes, audio_format: str) -> int:
    """Get audio duration in seconds."""
    audio_stream = BytesIO(audio_bytes)
    audio = AudioSegment.from_file(audio_stream, format=audio_format)
    return len(audio) // MS_PER_SECOND


async def transcribe_audio(
    audio_bytes: bytes,
    audio_format: str,
    language: str,
    provider: str = const.PROVIDER_WIT,
) -> tuple[str, int, int]:
    """
    Transcribe audio to text.

    Args:
        audio_bytes: Raw audio data
        audio_format: Format hint for pydub (e.g., "ogg", "opus", "mp4")
        language: Language code (en, ru, es, de)
        provider: Transcription provider (const.PROVIDER_WIT or const.PROVIDER_GROQ)

    Returns:
        Tuple of (transcribed text, duration in seconds, wit_requests_count).
        wit_requests_count is the number of Wit.ai API calls made (>1 for chunked audio),
        or 0 for non-Wit providers.
    """
    duration = get_audio_duration_seconds(audio_bytes, audio_format)

    if provider == const.PROVIDER_GROQ:
        text = await transcribe_with_groq(audio_bytes, language, audio_format)
        wit_requests = 0
    else:
        text, wit_requests = _transcribe_with_wit(audio_bytes, audio_format, language)

    logger.debug("Transcription result (%s): %s", provider, text)
    return text, duration, wit_requests


def _transcribe_with_wit(audio_bytes: bytes, audio_format: str, language: str) -> tuple[str, int]:
    """Wit.ai transcription. Returns (text, number_of_api_requests)."""
    audio_stream = BytesIO(audio_bytes)
    audio = AudioSegment.from_file(audio_stream, format=audio_format)

    chunks = [audio[i : i + CHUNK_LENGTH_MS] for i in range(0, len(audio), CHUNK_LENGTH_MS)]

    translator = voice_translators[language]
    full_text = ""

    for chunk in chunks:
        converted_stream = BytesIO()
        chunk.export(converted_stream, format="mp3")
        converted_stream.seek(0)

        response = translator.speech(
            audio_file=converted_stream, headers={"Content-Type": "audio/mpeg3"}
        )
        full_text += response.get("text", "")

    return full_text, len(chunks)
