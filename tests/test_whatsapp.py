from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import evlampiy.whatsapp.client
from evlampiy.credits import add_credits, current_month_key, deduct_credits, get_credits
from evlampiy.dto import WitUsageStats
from evlampiy.mongo import set_auto_categorize, set_chat_language, set_github_settings
from evlampiy.services.admin_service import block_user
from evlampiy.whatsapp.client import WHATSAPP_CHAT_PREFIX, init_whatsapp_client, whatsapp_state
from evlampiy.whatsapp.handlers import handle_link_command, handle_voice_message, register_handlers
from evlampiy.wit_tracking import get_wit_usage_this_month


class TestWhatsAppClient:
    """Test WhatsApp client initialization."""

    def test_returns_none_without_config(self):
        """Returns None when WhatsApp is not configured."""
        with patch("evlampiy.whatsapp.client.settings") as mock_settings:
            mock_settings.whatsapp_token = ""
            mock_settings.whatsapp_phone_id = ""
            evlampiy.whatsapp.client._WhatsAppClientHolder.instance = None

            result = init_whatsapp_client(FastAPI())
            assert result is None

    def test_creates_client_with_config(self):
        """Creates WhatsApp client when configured."""
        with patch("evlampiy.whatsapp.client.settings") as mock_settings:
            mock_settings.whatsapp_token = "test_token"
            mock_settings.whatsapp_phone_id = "123456789"
            mock_settings.whatsapp_app_id = ""
            mock_settings.whatsapp_app_secret = "app_secret"
            mock_settings.whatsapp_verify_token = "verify_token"
            evlampiy.whatsapp.client._WhatsAppClientHolder.instance = None

            app = FastAPI()
            with patch("evlampiy.whatsapp.client.WhatsApp") as mock_wa_class:
                result = init_whatsapp_client(app)
                mock_wa_class.assert_called_once()
                # server must be wired to the FastAPI app for pywa to register routes
                assert mock_wa_class.call_args.kwargs["server"] is app
                assert mock_wa_class.call_args.kwargs["app_secret"] == "app_secret"
                assert result is not None

    def test_refuses_the_webhook_without_an_app_secret(self, caplog):
        """Without the secret pywa stops checking signatures: anyone could post forged updates."""
        with patch("evlampiy.whatsapp.client.settings") as mock_settings:
            mock_settings.whatsapp_token = "test_token"
            mock_settings.whatsapp_phone_id = "123456789"
            mock_settings.whatsapp_app_secret = ""
            mock_settings.whatsapp_verify_token = "verify_token"
            evlampiy.whatsapp.client._WhatsAppClientHolder.instance = None

            with patch("evlampiy.whatsapp.client.WhatsApp") as mock_wa_class:
                result = init_whatsapp_client(FastAPI())

        assert result is None
        mock_wa_class.assert_not_called()
        assert [r.levelname for r in caplog.records if "WHATSAPP_APP_SECRET" in r.getMessage()] == ["ERROR"]

    @pytest.mark.parametrize(
        ("token", "phone_id", "app_secret", "state"),
        [
            ("", "", "", "off"),
            ("test_token", "", "app_secret", "off"),
            ("test_token", "123456789", "", "no app secret"),
            ("test_token", "123456789", "app_secret", "on"),
        ],
    )
    def test_whatsapp_state(self, token, phone_id, app_secret, state):
        with patch("evlampiy.whatsapp.client.settings") as mock_settings:
            mock_settings.whatsapp_token = token
            mock_settings.whatsapp_phone_id = phone_id
            mock_settings.whatsapp_app_secret = app_secret

            assert whatsapp_state() == state


class TestWhatsAppWebhook:
    """Test WhatsApp webhook endpoints."""

    def test_health_check(self, fastapi_app_no_whatsapp):
        """Health endpoint returns ok."""
        client = TestClient(fastapi_app_no_whatsapp)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "whatsapp": "off"}


class TestHandleVoiceMessage:
    """A linked number is its Telegram user's private chat (ADR-001); an unlinked one is told how to link."""

    async def test_handles_voice_message(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """A linked number's voice message is transcribed and sent back."""
        await link_whatsapp("1234567890", "70001")
        mock_whatsapp_message.from_user.wa_id = "1234567890"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once_with(to="1234567890", text="Hello world")

    async def test_an_unlinked_number_is_told_how_to_link(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """No Telegram account behind the number: no transcription, only the way to link."""
        await set_chat_language("wa_1234567891", "en")
        mock_whatsapp_message.from_user.wa_id = "1234567891"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        whatsapp_voice_external_mocks["transcribe"].assert_not_called()
        mock_whatsapp_client.send_message.assert_called_once_with(
            to="1234567891",
            text=(
                "To use the bot on WhatsApp, link it to your Telegram account: send /link_whatsapp "
                "to the bot in Telegram, then send the code here as: link XXXXXX"
            ),
        )

    async def test_skips_empty_transcription(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """Empty transcription produces no response."""
        await link_whatsapp("2234567890", "70002")
        mock_whatsapp_message.from_user.wa_id = "2234567890"
        whatsapp_voice_external_mocks["transcribe"].return_value = ("", 0, 0)

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_not_called()

    async def test_the_language_is_the_linked_users(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """The language set in the user's private Telegram chat is the one WhatsApp transcribes in."""
        await link_whatsapp("3234567890", "70003")
        await set_chat_language("u_70003", "de")
        mock_whatsapp_message.from_user.wa_id = "3234567890"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        assert whatsapp_voice_external_mocks["transcribe"].call_args.kwargs["language"] == "de"

    async def test_the_note_goes_to_the_linked_users_vault(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """The note is saved with the settings of the user's private Telegram chat, its vault included."""
        await link_whatsapp("3334567890", "70013")
        mock_whatsapp_message.from_user.wa_id = "3334567890"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        assert whatsapp_voice_external_mocks["save"].call_args.kwargs["settings_chat_id"] == "u_70013"

    async def test_handles_download_error(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """Download error is logged, no crash."""
        await link_whatsapp("4234567890", "70004")
        mock_whatsapp_message.from_user.wa_id = "4234567890"
        whatsapp_voice_external_mocks["http_client"].get.side_effect = Exception("Download failed")

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_not_called()

    async def test_voice_from_a_username_account_is_refused(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks
    ):
        """No phone number, no chat to key the note by: refuse, answering by BSUID."""
        mock_whatsapp_message.from_user.wa_id = None
        mock_whatsapp_message.from_user.bsuid = "US.13491208655302741918"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        whatsapp_voice_external_mocks["transcribe"].assert_not_called()
        mock_whatsapp_client.send_message.assert_called_once_with(
            to="US.13491208655302741918",
            text="Sorry, this bot doesn't support WhatsApp accounts with a username yet.",
        )

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
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """Auto-sorting set in the user's private Telegram chat sorts the WhatsApp note too."""
        await link_whatsapp("5234567890", "70005")
        await set_github_settings("u_70005", "owner", "repo", "token")
        await set_auto_categorize("u_70005", True)
        mock_whatsapp_message.from_user.wa_id = "5234567890"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        whatsapp_voice_external_mocks["categorize"].assert_called_once()
        mock_whatsapp_client.send_message.assert_called_once()

    async def test_cleanup_called_for_linked_paid_user(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """Transcript cleanup is called for paid users with auto_cleanup enabled."""
        await link_whatsapp("6234567890", "70006")
        await add_credits("70006", 50)  # a purchase makes the tier paid
        mock_whatsapp_message.from_user.wa_id = "6234567890"
        mocks = whatsapp_voice_external_mocks
        mocks["transcribe"].return_value = ("raw text", 5, 1)
        mocks["cleanup"].side_effect = lambda t, **kwargs: f"clean {t}"

        with patch("evlampiy.services.voice_pipeline.get_auto_cleanup", AsyncMock(return_value=True)):
            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mocks["cleanup"].assert_called_once_with("raw text", context=[])
        mock_whatsapp_client.send_message.assert_called_once_with(to="6234567890", text="clean raw text")

    async def test_cleanup_skipped_for_free_user(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """Transcript cleanup is NOT called for free users."""
        await link_whatsapp("7234567890", "70007")
        mock_whatsapp_message.from_user.wa_id = "7234567890"
        mocks = whatsapp_voice_external_mocks
        mocks["transcribe"].return_value = ("raw text", 5, 1)

        with patch("evlampiy.services.voice_pipeline.get_auto_cleanup", AsyncMock(return_value=True)):
            await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        mocks["cleanup"].assert_not_called()
        mock_whatsapp_client.send_message.assert_called_once_with(to="7234567890", text="raw text")

    async def test_a_blocked_users_number_is_refused(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """Blocking the Telegram user blocks the number linked to them."""
        await link_whatsapp("8234567890", "70008")
        await block_user("70008", admin_id="999")
        await set_chat_language("u_70008", "en")
        mock_whatsapp_message.from_user.wa_id = "8234567890"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        whatsapp_voice_external_mocks["transcribe"].assert_not_called()
        mock_whatsapp_client.send_message.assert_called_once_with(
            to="8234567890", text="You are blocked from using this bot."
        )

    async def test_a_message_spends_the_users_tokens_and_counts_wit(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """Five seconds through Wit.ai: one of the 10 free tokens, one Wit request, and the Wit alerts checked."""
        await link_whatsapp("9234567890", "70009")
        mock_whatsapp_message.from_user.wa_id = "9234567890"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        assert await get_credits("70009") == (9, 0)
        assert await get_wit_usage_this_month("ru") == 1
        whatsapp_voice_external_mocks["alerts"].assert_called_once_with()

    async def test_without_tokens_the_reply_points_to_telegram(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """WhatsApp sells nothing: a user out of tokens is sent to /buy in Telegram."""
        await link_whatsapp("9334567890", "70010")
        await deduct_credits("70010", 10)  # the month's free tokens, spent
        await set_chat_language("u_70010", "en")
        mock_whatsapp_message.from_user.wa_id = "9334567890"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        whatsapp_voice_external_mocks["transcribe"].assert_not_called()
        mock_whatsapp_client.send_message.assert_called_once_with(
            to="9334567890", text="Not enough tokens. Top up in the bot in Telegram with /buy."
        )

    async def test_at_the_wit_limit_a_free_user_is_refused(
        self, mock_whatsapp_client, mock_whatsapp_message, whatsapp_voice_external_mocks, link_whatsapp
    ):
        """500 of the 500 free Wit requests used: a free user has no provider left."""
        await link_whatsapp("9434567890", "70011")
        await set_chat_language("u_70011", "en")
        await WitUsageStats(month_key=current_month_key(), language="en", request_count=500).insert()
        mock_whatsapp_message.from_user.wa_id = "9434567890"

        await handle_voice_message(mock_whatsapp_client, mock_whatsapp_message)

        whatsapp_voice_external_mocks["transcribe"].assert_not_called()
        mock_whatsapp_client.send_message.assert_called_once_with(
            to="9434567890", text="Transcription service is temporarily unavailable. Please try again later."
        )


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

    async def test_routes_voice_to_handle_voice_message(self, mock_whatsapp_client, mock_whatsapp_message):
        """Voice messages are routed to handle_voice_message."""
        mock_wa = MagicMock()
        handler = self._capture_handler(mock_wa)

        mock_whatsapp_message.text = None
        mock_whatsapp_message.voice = MagicMock()
        mock_whatsapp_message.audio = None

        with patch("evlampiy.whatsapp.handlers.handle_voice_message", AsyncMock()) as mock_voice:
            await handler(mock_whatsapp_client, mock_whatsapp_message)
            mock_voice.assert_called_once_with(mock_whatsapp_client, mock_whatsapp_message)

    async def test_routes_link_command_to_handle_link_command(self, mock_whatsapp_client, mock_whatsapp_message):
        """Link commands are routed to handle_link_command."""
        mock_wa = MagicMock()
        handler = self._capture_handler(mock_wa)

        mock_whatsapp_message.text = "link ABC123"
        mock_whatsapp_message.voice = None
        mock_whatsapp_message.audio = None

        with patch("evlampiy.whatsapp.handlers.handle_link_command", AsyncMock()) as mock_link:
            await handler(mock_whatsapp_client, mock_whatsapp_message)
            mock_link.assert_called_once_with(mock_whatsapp_client, mock_whatsapp_message)

    async def test_ignores_non_voice_non_link_messages(self, mock_whatsapp_client, mock_whatsapp_message):
        """Messages that are neither voice nor link are silently ignored."""
        mock_wa = MagicMock()
        handler = self._capture_handler(mock_wa)

        mock_whatsapp_message.text = "Hello there"
        mock_whatsapp_message.voice = None
        mock_whatsapp_message.audio = None

        with (
            patch("evlampiy.whatsapp.handlers.handle_voice_message", AsyncMock()) as mock_voice,
            patch("evlampiy.whatsapp.handlers.handle_link_command", AsyncMock()) as mock_link,
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

        with patch("evlampiy.services.account_linking_service.confirm_link", AsyncMock(return_value="rate_limited")):
            await handle_link_command(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once()
        call_kwargs = mock_whatsapp_client.send_message.call_args.kwargs
        assert "wait" in call_kwargs["text"].lower()

    async def test_link_invalid_code(self, mock_whatsapp_client, mock_whatsapp_message):
        """Link command with invalid code shows error."""
        mock_whatsapp_message.text = "link INVALID"

        with patch("evlampiy.services.account_linking_service.confirm_link", AsyncMock(return_value="invalid")):
            await handle_link_command(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once()
        call_kwargs = mock_whatsapp_client.send_message.call_args.kwargs
        assert "Invalid" in call_kwargs["text"]

    async def test_link_success(self, mock_whatsapp_client, mock_whatsapp_message):
        """Link command with valid code succeeds."""
        mock_whatsapp_message.text = "link VALID123"

        with patch("evlampiy.services.account_linking_service.confirm_link", AsyncMock(return_value="success")):
            await handle_link_command(mock_whatsapp_client, mock_whatsapp_message)

        mock_whatsapp_client.send_message.assert_called_once()
        call_kwargs = mock_whatsapp_client.send_message.call_args.kwargs
        assert "successfully" in call_kwargs["text"]

    async def test_link_from_a_username_account_is_refused(self, mock_whatsapp_client, mock_whatsapp_message):
        """A username hides the phone number that links are keyed by: refuse, answering by BSUID."""
        mock_whatsapp_message.text = "link VALID123"
        mock_whatsapp_message.from_user.wa_id = None
        mock_whatsapp_message.from_user.bsuid = "US.13491208655302741918"

        with patch("evlampiy.services.account_linking_service.confirm_link", AsyncMock()) as confirm:
            await handle_link_command(mock_whatsapp_client, mock_whatsapp_message)

        confirm.assert_not_called()
        mock_whatsapp_client.send_message.assert_called_once_with(
            to="US.13491208655302741918",
            text="Sorry, this bot doesn't support WhatsApp accounts with a username yet.",
        )
