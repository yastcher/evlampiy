"""Voice transcription service — platform-agnostic."""

import logging
from io import BytesIO

from pydub import AudioSegment

from src.transcription.wit_client import voice_translators

logger = logging.getLogger(__name__)

CHUNK_LENGTH_MS = 19500  # Wit.ai limit: <20 sec


def transcribe_audio(audio_bytes: bytes, audio_format: str, language: str) -> str:
    """
    Transcribe audio to text using Wit.ai.

    Args:
        audio_bytes: Raw audio data
        audio_format: Format hint for pydub (e.g., "ogg", "opus", "mp4")
        language: Language code (en, ru, es, de)

    Returns:
        Transcribed text or empty string
    """
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

    logger.debug("Transcription result: %s", full_text)
    return full_text
