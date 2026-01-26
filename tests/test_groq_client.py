"""Integration tests for Groq Whisper client."""

from unittest.mock import MagicMock, patch

import httpx

from src.transcription.groq_client import transcribe_with_groq


class TestGroqClient:

    async def test_transcribes_audio_successfully(self):
        """Successful transcription returns text."""
        mock_response = MagicMock()
        mock_response.text = "Hello world"
        mock_response.raise_for_status = MagicMock()

        with (
            patch("src.transcription.groq_client.settings") as mock_settings,
            patch("src.transcription.groq_client.httpx.AsyncClient") as mock_client_class,
        ):
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "whisper-large-v3-turbo"
            mock_client_class.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await transcribe_with_groq(b"audio", "en")

            assert result == "Hello world"

    async def test_returns_empty_on_api_error(self):
        """API error returns empty string, doesn't raise."""
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with (
            patch("src.transcription.groq_client.settings") as mock_settings,
            patch("src.transcription.groq_client.httpx.AsyncClient") as mock_client_class,
        ):
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "whisper-large-v3-turbo"
            mock_client_class.return_value.__aenter__.return_value.post.side_effect = (
                httpx.HTTPStatusError(
                    "Error", request=mock_request, response=mock_response
                )
            )

            result = await transcribe_with_groq(b"audio", "en")

            assert result == ""

    async def test_returns_empty_on_request_error(self):
        """Network error returns empty string, doesn't raise."""
        with (
            patch("src.transcription.groq_client.settings") as mock_settings,
            patch("src.transcription.groq_client.httpx.AsyncClient") as mock_client_class,
        ):
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "whisper-large-v3-turbo"
            mock_client_class.return_value.__aenter__.return_value.post.side_effect = (
                httpx.RequestError("Connection failed", request=MagicMock())
            )

            result = await transcribe_with_groq(b"audio", "en")

            assert result == ""

    async def test_returns_empty_when_not_configured(self):
        """Returns empty if GROQ_API_KEY not set."""
        with patch("src.transcription.groq_client.settings") as mock_settings:
            mock_settings.groq_api_key = ""

            result = await transcribe_with_groq(b"audio", "en")

            assert result == ""

    async def test_passes_audio_format_in_filename(self):
        """Audio format is used in the filename hint."""
        mock_response = MagicMock()
        mock_response.text = "result"
        mock_response.raise_for_status = MagicMock()

        with (
            patch("src.transcription.groq_client.settings") as mock_settings,
            patch("src.transcription.groq_client.httpx.AsyncClient") as mock_client_class,
        ):
            mock_settings.groq_api_key = "test-key"
            mock_settings.groq_model = "whisper-large-v3-turbo"
            mock_post = mock_client_class.return_value.__aenter__.return_value.post
            mock_post.return_value = mock_response

            await transcribe_with_groq(b"audio", "ru", audio_format="mp4")

            call_kwargs = mock_post.call_args
            files = call_kwargs.kwargs["files"]
            filename = files["file"][0]
            assert filename == "audio.mp4"
