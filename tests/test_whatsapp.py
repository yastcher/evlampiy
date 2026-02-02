from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.main import create_fastapi_app
from src.mongo import set_auto_categorize, set_chat_language, set_github_settings
from src.whatsapp.client import WHATSAPP_CHAT_PREFIX, get_whatsapp_client
from src.whatsapp.handlers import handle_link_command, handle_voice_message


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
        with patch("src.whatsapp.client.get_whatsapp_client", return_value=None):
            app = create_fastapi_app()
            client = TestClient(app)

            response = client.get("/health")

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


class TestHandleVoiceMessage:
    """Test WhatsApp voice message handler."""

    async def test_handles_voice_message(
        self, mock_whatsapp_client, mock_whatsapp_message, mock_httpx_download_response
    ):
        """Voice message is transcribed and sent back."""
        phone_number = "1234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "en")

        mock_whatsapp_message.from_user.wa_id = phone_number

        with (
            patch("src.whatsapp.handlers.transcribe_audio", AsyncMock(return_value=("Hello world", 5))),
            patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
            patch("src.whatsapp.handlers.save_transcription_to_obsidian", AsyncMock(return_value=(True, "test.md"))),
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_httpx_download_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

            mock_whatsapp_client.send_message.assert_called_once_with(to=phone_number, text="Hello world")

    async def test_skips_empty_transcription(
        self, mock_whatsapp_client, mock_whatsapp_message, mock_httpx_download_response
    ):
        """Empty transcription produces no response."""
        phone_number = "2234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "en")

        mock_whatsapp_message.from_user.wa_id = phone_number

        with (
            patch("src.whatsapp.handlers.transcribe_audio", AsyncMock(return_value=("", 0))),
            patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_httpx_download_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

            mock_whatsapp_client.send_message.assert_not_called()

    async def test_uses_whatsapp_chat_prefix(
        self, mock_whatsapp_client, mock_whatsapp_message, mock_httpx_download_response
    ):
        """Chat ID uses WhatsApp prefix for language lookup."""
        phone_number = "3234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "de")

        mock_whatsapp_message.from_user.wa_id = phone_number

        with (
            patch("src.whatsapp.handlers.transcribe_audio", AsyncMock(return_value=("Test", 3))) as mock_transcribe,
            patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
            patch("src.whatsapp.handlers.save_transcription_to_obsidian", AsyncMock(return_value=(True, "test.md"))),
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_httpx_download_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

            # Verify transcribe_audio was called with correct language from DB
            call_kwargs = mock_transcribe.call_args.kwargs
            assert call_kwargs["language"] == "de"

    async def test_handles_download_error(self, mock_whatsapp_client, mock_whatsapp_message):
        """Download error is logged, no crash."""
        phone_number = "4234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "en")

        mock_whatsapp_message.from_user.wa_id = phone_number

        with patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Download failed"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Should not raise
            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

            mock_whatsapp_client.send_message.assert_not_called()

    def test_whatsapp_chat_prefix_value(self):
        """WHATSAPP_CHAT_PREFIX has correct value."""
        assert WHATSAPP_CHAT_PREFIX == "wa_"

    async def test_no_audio_returns_early(self, mock_whatsapp_client, mock_whatsapp_message):
        """Handler returns early when no audio attached."""
        mock_whatsapp_message.voice = None
        mock_whatsapp_message.audio = None

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_not_called()

    async def test_auto_categorize_flow(
        self, mock_whatsapp_client, mock_whatsapp_message, mock_httpx_download_response
    ):
        """Voice message triggers auto-categorization when enabled."""
        phone_number = "5234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "en")
        await set_github_settings(chat_id, "owner", "repo", "token")
        await set_auto_categorize(chat_id, True)

        mock_whatsapp_message.from_user.wa_id = phone_number

        with (
            patch("src.whatsapp.handlers.transcribe_audio", AsyncMock(return_value=("Note text", 5))),
            patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
            patch("src.whatsapp.handlers.save_transcription_to_obsidian", AsyncMock(return_value=(True, "note.md"))),
            patch("src.whatsapp.handlers.categorize_note", AsyncMock(return_value="work")) as mock_categorize,
        ):
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_httpx_download_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

            mock_categorize.assert_called_once()
            mock_whatsapp_client.send_message.assert_called_once()


class TestHandleLinkCommand:
    """Test WhatsApp account linking command."""

    async def test_link_without_code_shows_usage(self, mock_whatsapp_client, mock_whatsapp_message):
        """Link command without code shows usage message."""
        mock_whatsapp_message.text = "link "

        await handle_link_command(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once()
        call_kwargs = mock_whatsapp_client.send_message.call_args.kwargs
        assert "Usage" in call_kwargs["text"]

    async def test_link_rate_limited(self, mock_whatsapp_client, mock_whatsapp_message):
        """Link command with rate limiting shows wait message."""
        mock_whatsapp_message.text = "link ABC123"

        with patch("src.whatsapp.handlers.confirm_link", AsyncMock(return_value="rate_limited")):
            await handle_link_command(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once()
        call_kwargs = mock_whatsapp_client.send_message.call_args.kwargs
        assert "wait" in call_kwargs["text"].lower()

    async def test_link_invalid_code(self, mock_whatsapp_client, mock_whatsapp_message):
        """Link command with invalid code shows error."""
        mock_whatsapp_message.text = "link INVALID"

        with patch("src.whatsapp.handlers.confirm_link", AsyncMock(return_value="invalid")):
            await handle_link_command(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once()
        call_kwargs = mock_whatsapp_client.send_message.call_args.kwargs
        assert "Invalid" in call_kwargs["text"]

    async def test_link_success(self, mock_whatsapp_client, mock_whatsapp_message):
        """Link command with valid code succeeds."""
        mock_whatsapp_message.text = "link VALID123"

        with patch("src.whatsapp.handlers.confirm_link", AsyncMock(return_value="success")):
            await handle_link_command(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once()
        call_kwargs = mock_whatsapp_client.send_message.call_args.kwargs
        assert "successfully" in call_kwargs["text"]
