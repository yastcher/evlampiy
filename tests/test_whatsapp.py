from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.whatsapp.client import WHATSAPP_CHAT_PREFIX, get_whatsapp_client
from src.whatsapp.handlers import handle_voice_message


class TestWhatsAppClient:
    """Test WhatsApp client initialization."""

    def test_returns_none_without_config(self):
        """Returns None when WhatsApp is not configured."""
        with patch("src.whatsapp.client.settings") as mock_settings:
            mock_settings.whatsapp_token = ""
            mock_settings.whatsapp_phone_id = ""
            # Reset cached client
            import src.whatsapp.client

            src.whatsapp.client._wa_client = None

            result = get_whatsapp_client()
            assert result is None

    def test_creates_client_with_config(self):
        """Creates WhatsApp client when configured."""
        with patch("src.whatsapp.client.settings") as mock_settings:
            mock_settings.whatsapp_token = "test_token"
            mock_settings.whatsapp_phone_id = "123456789"
            mock_settings.whatsapp_app_id = ""
            mock_settings.whatsapp_app_secret = ""
            mock_settings.whatsapp_verify_token = "verify_token"
            # Reset cached client
            import src.whatsapp.client

            src.whatsapp.client._wa_client = None

            with patch("src.whatsapp.client.WhatsApp") as mock_wa_class:
                result = get_whatsapp_client()
                mock_wa_class.assert_called_once()
                assert result is not None


class TestWhatsAppWebhook:
    """Test WhatsApp webhook endpoints."""

    def test_health_check(self):
        """Health endpoint returns ok."""
        from src.main import create_fastapi_app

        with patch("src.whatsapp.client.get_whatsapp_client", return_value=None):
            app = create_fastapi_app()
            client = TestClient(app)

            response = client.get("/health")

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestHandleVoiceMessage:
    """Test WhatsApp voice message handler."""

    @pytest.mark.asyncio
    async def test_handles_voice_message(self):
        """Voice message is transcribed and sent back."""
        mock_wa = MagicMock()
        mock_wa.get_media_url.return_value = "https://example.com/audio.ogg"
        mock_wa.send_message = MagicMock()

        mock_message = MagicMock()
        mock_message.from_user.wa_id = "1234567890"
        mock_message.voice = MagicMock()
        mock_message.voice.id = "media_123"
        mock_message.audio = None

        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"
        mock_response.raise_for_status = MagicMock()

        with (
            patch("src.whatsapp.handlers.get_chat_language", AsyncMock(return_value="en")),
            patch("src.whatsapp.handlers.transcribe_audio", return_value="Hello world"),
            patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
            patch("src.whatsapp.handlers.save_transcription_to_obsidian", AsyncMock()),
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await handle_voice_message(mock_wa, mock_message)

            mock_wa.send_message.assert_called_once_with(to="1234567890", text="Hello world")

    @pytest.mark.asyncio
    async def test_skips_empty_transcription(self):
        """Empty transcription produces no response."""
        mock_wa = MagicMock()
        mock_wa.get_media_url.return_value = "https://example.com/audio.ogg"
        mock_wa.send_message = MagicMock()

        mock_message = MagicMock()
        mock_message.from_user.wa_id = "1234567890"
        mock_message.voice = MagicMock()
        mock_message.voice.id = "media_123"
        mock_message.audio = None

        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"
        mock_response.raise_for_status = MagicMock()

        with (
            patch("src.whatsapp.handlers.get_chat_language", AsyncMock(return_value="en")),
            patch("src.whatsapp.handlers.transcribe_audio", return_value=""),
            patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await handle_voice_message(mock_wa, mock_message)

            mock_wa.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_whatsapp_chat_prefix(self):
        """Chat ID uses WhatsApp prefix."""
        mock_wa = MagicMock()
        mock_wa.get_media_url.return_value = "https://example.com/audio.ogg"
        mock_wa.send_message = MagicMock()

        mock_message = MagicMock()
        mock_message.from_user.wa_id = "1234567890"
        mock_message.voice = MagicMock()
        mock_message.voice.id = "media_123"
        mock_message.audio = None

        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"
        mock_response.raise_for_status = MagicMock()

        with (
            patch(
                "src.whatsapp.handlers.get_chat_language", AsyncMock(return_value="en")
            ) as mock_get_lang,
            patch("src.whatsapp.handlers.transcribe_audio", return_value="Test"),
            patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
            patch("src.whatsapp.handlers.save_transcription_to_obsidian", AsyncMock()),
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await handle_voice_message(mock_wa, mock_message)

            expected_chat_id = f"{WHATSAPP_CHAT_PREFIX}1234567890"
            mock_get_lang.assert_called_once_with(expected_chat_id)

    @pytest.mark.asyncio
    async def test_handles_download_error(self):
        """Download error is logged, no crash."""
        mock_wa = MagicMock()
        mock_wa.get_media_url.return_value = "https://example.com/audio.ogg"
        mock_wa.send_message = MagicMock()

        mock_message = MagicMock()
        mock_message.from_user.wa_id = "1234567890"
        mock_message.voice = MagicMock()
        mock_message.voice.id = "media_123"
        mock_message.audio = None

        with (
            patch("src.whatsapp.handlers.get_chat_language", AsyncMock(return_value="en")),
            patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Download failed"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Should not raise
            await handle_voice_message(mock_wa, mock_message)

            mock_wa.send_message.assert_not_called()

    def test_whatsapp_chat_prefix_value(self):
        """WHATSAPP_CHAT_PREFIX has correct value."""
        assert WHATSAPP_CHAT_PREFIX == "wa_"
