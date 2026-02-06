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
    use_groq: bool = False,
) -> tuple[str, int]:
    """
    Transcribe audio to text.

    Args:
        audio_bytes: Raw audio data
        audio_format: Format hint for pydub (e.g., "ogg", "opus", "mp4")
        language: Language code (en, ru, es, de)
        use_groq: If True, use Groq Whisper instead of Wit.ai

    Returns:
        Tuple of (transcribed text, duration in seconds)
    """
    duration = get_audio_duration_seconds(audio_bytes, audio_format)

    if use_groq:
        text = await transcribe_with_groq(audio_bytes, language, audio_format)
    else:
        text = _transcribe_with_wit(audio_bytes, audio_format, language)

    logger.debug(
        "Transcription result (%s): %s",
        const.PROVIDER_GROQ if use_groq else const.PROVIDER_WIT,
        text,
    )
    return text, duration


def _transcribe_with_wit(audio_bytes: bytes, audio_format: str, language: str) -> str:
    """Original Wit.ai transcription logic."""
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
        text = response.get("text", "")
        full_text += text

    return full_text
