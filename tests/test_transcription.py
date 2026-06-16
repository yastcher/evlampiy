import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src import const
from src.transcription.service import CHUNK_LENGTH_MS, transcribe_audio


class TestTranscribeAudio:
    """Test transcription service."""

    async def test_transcribes_short_audio(self, mock_audio_segment_factory):
        """Audio shorter than chunk length is transcribed in one call."""
        seg = mock_audio_segment_factory(5000)

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(return_value={"text": "Hello world"})

        with (
            patch("src.transcription.service.AudioSegment.from_file", return_value=seg),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            text, duration, _ = await transcribe_audio(b"audio_data", "ogg", "en")

            assert text == "Hello world"
            assert duration == 5
            mock_wit.speech.assert_called_once()

    async def test_transcribes_long_audio_in_chunks(self, mock_audio_segment_factory):
        """Audio longer than chunk length is split and transcribed."""
        # Audio of 40 seconds = 2 chunks
        audio_length = CHUNK_LENGTH_MS * 2 + 1000
        seg = mock_audio_segment_factory(audio_length)

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(
            side_effect=[
                {"text": "Part one. "},
                {"text": "Part two. "},
                {"text": "Part three."},
            ]
        )

        with (
            patch("src.transcription.service.AudioSegment.from_file", return_value=seg),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            text, duration, _ = await transcribe_audio(b"audio_data", "ogg", "en")

            assert text == "Part one. Part two. Part three."
            assert duration == 40
            assert mock_wit.speech.call_count == 3

    async def test_handles_missing_text_in_response(self, mock_audio_segment_factory):
        """Response without 'text' key returns empty string."""
        seg = mock_audio_segment_factory(5000)

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(return_value={})  # No 'text' key

        with (
            patch("src.transcription.service.AudioSegment.from_file", return_value=seg),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            text, _duration, _ = await transcribe_audio(b"audio_data", "ogg", "en")

            assert text == ""

    async def test_uses_correct_language_translator(self, mock_audio_segment_factory):
        """Correct language translator is used."""
        seg = mock_audio_segment_factory(5000)

        mock_wit_ru = MagicMock()
        mock_wit_ru.speech = MagicMock(return_value={"text": "Привет мир"})

        mock_wit_en = MagicMock()
        mock_wit_en.speech = MagicMock(return_value={"text": "Hello world"})

        with (
            patch("src.transcription.service.AudioSegment.from_file", return_value=seg),
            patch(
                "src.transcription.service.voice_translators",
                {"ru": mock_wit_ru, "en": mock_wit_en},
            ),
        ):
            text, _duration, _ = await transcribe_audio(b"audio_data", "ogg", "ru")

            assert text == "Привет мир"
            mock_wit_ru.speech.assert_called_once()
            mock_wit_en.speech.assert_not_called()

    async def test_exports_to_mp3_format(self, mock_audio_segment_factory):
        """Audio chunks are exported as MP3."""
        seg = mock_audio_segment_factory(5000)

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(return_value={"text": "Test"})

        with (
            patch("src.transcription.service.AudioSegment.from_file", return_value=seg),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            await transcribe_audio(b"audio_data", "ogg", "en")

            seg.export.assert_called_once()
            call_kwargs = seg.export.call_args
            assert call_kwargs[1]["format"] == "mp3"

    async def test_groq_transcription(self, mock_audio_segment_factory):
        """Groq path: raw audio bytes sent to Groq API with format hint."""
        seg = mock_audio_segment_factory(10000)

        mock_groq = AsyncMock(return_value="Groq result")

        with (
            patch("src.transcription.service.AudioSegment.from_file", return_value=seg),
            patch("src.transcription.service.transcribe_with_groq", mock_groq),
        ):
            text, duration, _ = await transcribe_audio(b"audio_data", "ogg", "en", provider=const.PROVIDER_GROQ)

            assert text == "Groq result"
            assert duration == 10
            mock_groq.assert_called_once_with(b"audio_data", "en", "ogg")

    async def test_returns_duration_in_seconds(self, mock_audio_segment_factory):
        """Duration is returned in seconds."""
        seg = mock_audio_segment_factory(15500)  # 15.5s -> 15s

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(return_value={"text": "Test"})

        with (
            patch("src.transcription.service.AudioSegment.from_file", return_value=seg),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            _, duration, _ = await transcribe_audio(b"audio_data", "ogg", "en")

            assert duration == 15


class TestTranscribeAudioConcurrency:
    """Transcription must not block the shared event loop.

    `get_audio_duration_seconds` (ffmpeg decode) and `_transcribe_with_wit`
    (ffmpeg decode + chunk export + synchronous wit.ai HTTP) are blocking. They
    share the event loop with Telegram polling and the WhatsApp FastAPI webhook,
    so they must be offloaded to a worker thread.
    """

    async def test_wit_path_does_not_block_event_loop(self):
        """A blocking transcription must not freeze concurrent loop work."""
        block_half = 0.1

        def blocking_duration(audio_bytes, audio_format):
            time.sleep(block_half)
            return 5

        def blocking_wit(audio_bytes, audio_format, language):
            time.sleep(block_half)
            return "hello", 1

        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep(0.01)

        ticker_task = asyncio.create_task(ticker())
        try:
            with (
                patch(
                    "src.transcription.service.get_audio_duration_seconds",
                    blocking_duration,
                ),
                patch("src.transcription.service._transcribe_with_wit", blocking_wit),
            ):
                await asyncio.sleep(0)  # let the ticker reach its first await
                text, duration, wit_requests = await transcribe_audio(b"audio", "ogg", "en")
        finally:
            ticker_task.cancel()

        assert text == "hello"
        assert duration == 5
        assert wit_requests == 1
        # 0.2s of blocking work on the loop would freeze the 10ms ticker (~1 tick).
        # Offloaded to a thread, it advances ~20 times. Floor well below that.
        assert ticks >= 5
