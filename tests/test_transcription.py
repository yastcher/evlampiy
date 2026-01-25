from unittest.mock import MagicMock, patch

from src.transcription.service import CHUNK_LENGTH_MS, transcribe_audio


class TestTranscribeAudio:
    """Test transcription service."""

    def test_transcribes_short_audio(self):
        """Audio shorter than chunk length is transcribed in one call."""
        mock_audio_segment = MagicMock()
        mock_audio_segment.__len__ = MagicMock(return_value=5000)  # 5 seconds
        mock_audio_segment.__getitem__ = MagicMock(return_value=mock_audio_segment)
        mock_audio_segment.export = MagicMock()

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(return_value={"text": "Hello world"})

        with (
            patch(
                "src.transcription.service.AudioSegment.from_file", return_value=mock_audio_segment
            ),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            result = transcribe_audio(b"audio_data", "ogg", "en")

            assert result == "Hello world"
            mock_wit.speech.assert_called_once()

    def test_transcribes_long_audio_in_chunks(self):
        """Audio longer than chunk length is split and transcribed."""
        # Audio of 40 seconds = 2 chunks
        audio_length = CHUNK_LENGTH_MS * 2 + 1000

        mock_audio_segment = MagicMock()
        mock_audio_segment.__len__ = MagicMock(return_value=audio_length)
        mock_audio_segment.__getitem__ = MagicMock(return_value=mock_audio_segment)
        mock_audio_segment.export = MagicMock()

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(
            side_effect=[
                {"text": "Part one. "},
                {"text": "Part two. "},
                {"text": "Part three."},
            ]
        )

        with (
            patch(
                "src.transcription.service.AudioSegment.from_file", return_value=mock_audio_segment
            ),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            result = transcribe_audio(b"audio_data", "ogg", "en")

            assert result == "Part one. Part two. Part three."
            assert mock_wit.speech.call_count == 3

    def test_handles_missing_text_in_response(self):
        """Response without 'text' key returns empty string."""
        mock_audio_segment = MagicMock()
        mock_audio_segment.__len__ = MagicMock(return_value=5000)
        mock_audio_segment.__getitem__ = MagicMock(return_value=mock_audio_segment)
        mock_audio_segment.export = MagicMock()

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(return_value={})  # No 'text' key

        with (
            patch(
                "src.transcription.service.AudioSegment.from_file", return_value=mock_audio_segment
            ),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            result = transcribe_audio(b"audio_data", "ogg", "en")

            assert result == ""

    def test_uses_correct_language_translator(self):
        """Correct language translator is used."""
        mock_audio_segment = MagicMock()
        mock_audio_segment.__len__ = MagicMock(return_value=5000)
        mock_audio_segment.__getitem__ = MagicMock(return_value=mock_audio_segment)
        mock_audio_segment.export = MagicMock()

        mock_wit_ru = MagicMock()
        mock_wit_ru.speech = MagicMock(return_value={"text": "Привет мир"})

        mock_wit_en = MagicMock()
        mock_wit_en.speech = MagicMock(return_value={"text": "Hello world"})

        with (
            patch(
                "src.transcription.service.AudioSegment.from_file", return_value=mock_audio_segment
            ),
            patch(
                "src.transcription.service.voice_translators",
                {"ru": mock_wit_ru, "en": mock_wit_en},
            ),
        ):
            result = transcribe_audio(b"audio_data", "ogg", "ru")

            assert result == "Привет мир"
            mock_wit_ru.speech.assert_called_once()
            mock_wit_en.speech.assert_not_called()

    def test_exports_to_mp3_format(self):
        """Audio chunks are exported as MP3."""
        mock_audio_segment = MagicMock()
        mock_audio_segment.__len__ = MagicMock(return_value=5000)
        mock_audio_segment.__getitem__ = MagicMock(return_value=mock_audio_segment)
        mock_export = MagicMock()
        mock_audio_segment.export = mock_export

        mock_wit = MagicMock()
        mock_wit.speech = MagicMock(return_value={"text": "Test"})

        with (
            patch(
                "src.transcription.service.AudioSegment.from_file", return_value=mock_audio_segment
            ),
            patch("src.transcription.service.voice_translators", {"en": mock_wit}),
        ):
            transcribe_audio(b"audio_data", "ogg", "en")

            mock_export.assert_called_once()
            call_kwargs = mock_export.call_args
            assert call_kwargs[1]["format"] == "mp3"
