from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

import src.whatsapp.client
from src.dto import UserTier
from src.mongo import set_auto_categorize, set_chat_language, set_github_settings
from src.whatsapp.app import create_fastapi_app
from src.whatsapp.client import WHATSAPP_CHAT_PREFIX, get_whatsapp_client
from src.whatsapp.handlers import handle_link_command, handle_voice_message, register_handlers


class TestWhatsAppClient:
    """Test WhatsApp client initialization."""

    def test_returns_none_without_config(self):
        """Returns None when WhatsApp is not configured."""
        with patch("src.whatsapp.client.settings") as mock_settings:
            mock_settings.whatsapp_token = ""
            mock_settings.whatsapp_phone_id = ""
            # Reset cached client

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
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """Voice message is transcribed and sent back."""
        phone_number = "1234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "en")
        mock_whatsapp_message.from_user.wa_id = phone_number

        mocks = whatsapp_voice_external_mocks
        mocks["transcribe"].return_value = ("Hello world", 5, 1)

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once_with(
            to=phone_number, text="Hello world"
        )

    async def test_skips_empty_transcription(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """Empty transcription produces no response."""
        phone_number = "2234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "en")
        mock_whatsapp_message.from_user.wa_id = phone_number

        mocks = whatsapp_voice_external_mocks
        mocks["transcribe"].return_value = ("", 0, 0)

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_not_called()

    async def test_uses_whatsapp_chat_prefix(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """Chat ID uses WhatsApp prefix for language lookup."""
        phone_number = "3234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "de")
        mock_whatsapp_message.from_user.wa_id = phone_number

        mocks = whatsapp_voice_external_mocks
        mocks["transcribe"].return_value = ("Test", 3, 1)

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        # Verify transcribe_audio was called with correct language from DB
        call_kwargs = mocks["transcribe"].call_args.kwargs
        assert call_kwargs["language"] == "de"

    async def test_handles_download_error(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """Download error is logged, no crash."""
        phone_number = "4234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "en")
        mock_whatsapp_message.from_user.wa_id = phone_number

        mocks = whatsapp_voice_external_mocks
        mocks["http_client"].get.side_effect = Exception("Download failed")

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
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """Voice message triggers auto-categorization when enabled."""
        phone_number = "5234567890"
        chat_id = f"{WHATSAPP_CHAT_PREFIX}{phone_number}"
        await set_chat_language(chat_id, "en")
        await set_github_settings(chat_id, "owner", "repo", "token")
        await set_auto_categorize(chat_id, True)
        mock_whatsapp_message.from_user.wa_id = phone_number

        mocks = whatsapp_voice_external_mocks
        mocks["transcribe"].return_value = ("Note text", 5, 1)

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mocks["categorize"].assert_called_once()
        mock_whatsapp_client.send_message.assert_called_once()

    async def test_cleanup_called_for_linked_paid_user(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """Transcript cleanup is called for paid users with auto_cleanup enabled."""
        phone_number = "6234567890"
        mock_whatsapp_message.from_user.wa_id = phone_number

        mocks = whatsapp_voice_external_mocks
        mocks["transcribe"].return_value = ("raw text", 5, 1)
        mocks["cleanup"].side_effect = lambda t, **kwargs: f"clean {t}"

        with (
            patch("src.whatsapp.handlers.get_linked_telegram_id", AsyncMock(return_value="99999")),
            patch("src.whatsapp.handlers.get_auto_cleanup", AsyncMock(return_value=True)),
            patch("src.whatsapp.handlers.get_user_tier", AsyncMock(return_value=UserTier.PAID)),
        ):
            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mocks["cleanup"].assert_called_once_with("raw text", context=[])
        mock_whatsapp_client.send_message.assert_called_once_with(
            to=phone_number, text="clean raw text"
        )

    async def test_cleanup_skipped_for_free_user(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """Transcript cleanup is NOT called for free users."""
        phone_number = "7234567890"
        mock_whatsapp_message.from_user.wa_id = phone_number

        mocks = whatsapp_voice_external_mocks
        mocks["transcribe"].return_value = ("raw text", 5, 1)

        with (
            patch("src.whatsapp.handlers.get_linked_telegram_id", AsyncMock(return_value="99998")),
            patch("src.whatsapp.handlers.get_auto_cleanup", AsyncMock(return_value=True)),
            patch("src.whatsapp.handlers.get_user_tier", AsyncMock(return_value=UserTier.FREE)),
        ):
            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mocks["cleanup"].assert_not_called()
        mock_whatsapp_client.send_message.assert_called_once_with(to=phone_number, text="raw text")


class TestHandleMessageRouter:
    """Test handle_message routing logic."""

    def _capture_handler(self, mock_wa):
        """Register handlers on mock_wa and capture the handle_message function."""
        captured = {}

        def on_message_decorator():
            def decorator(fn):
                captured["handler"] = fn
                return fn

            return decorator

        mock_wa.on_message = on_message_decorator
        register_handlers(mock_wa)
        return captured["handler"]

    async def test_routes_voice_to_handle_voice_message(
        self, mock_whatsapp_client, mock_whatsapp_message
    ):
        """Voice messages are routed to handle_voice_message."""
        mock_wa = MagicMock()
        handler = self._capture_handler(mock_wa)

        mock_whatsapp_message.text = None
        mock_whatsapp_message.voice = MagicMock()
        mock_whatsapp_message.audio = None

        with patch("src.whatsapp.handlers.handle_voice_message", AsyncMock()) as mock_voice:
            await handler(mock_whatsapp_client, mock_whatsapp_message)
            mock_voice.assert_called_once_with(mock_whatsapp_client, mock_whatsapp_message)

    async def test_routes_link_command_to_handle_link_command(
        self, mock_whatsapp_client, mock_whatsapp_message
    ):
        """Link commands are routed to handle_link_command."""
        mock_wa = MagicMock()
        handler = self._capture_handler(mock_wa)

        mock_whatsapp_message.text = "link ABC123"
        mock_whatsapp_message.voice = None
        mock_whatsapp_message.audio = None

        with patch("src.whatsapp.handlers.handle_link_command", AsyncMock()) as mock_link:
            await handler(mock_whatsapp_client, mock_whatsapp_message)
            mock_link.assert_called_once_with(mock_whatsapp_client, mock_whatsapp_message)

    async def test_ignores_non_voice_non_link_messages(
        self, mock_whatsapp_client, mock_whatsapp_message
    ):
        """Messages that are neither voice nor link are silently ignored."""
        mock_wa = MagicMock()
        handler = self._capture_handler(mock_wa)

        mock_whatsapp_message.text = "Hello there"
        mock_whatsapp_message.voice = None
        mock_whatsapp_message.audio = None

        with (
            patch("src.whatsapp.handlers.handle_voice_message", AsyncMock()) as mock_voice,
            patch("src.whatsapp.handlers.handle_link_command", AsyncMock()) as mock_link,
        ):
            await handler(mock_whatsapp_client, mock_whatsapp_message)
            mock_voice.assert_not_called()
            mock_link.assert_not_called()


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
