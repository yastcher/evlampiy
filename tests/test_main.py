"""Entrypoint wiring (`src.main._async_main`)."""

from unittest.mock import AsyncMock, patch

from src.config import settings
from src.main import _async_main


class TestAsyncMain:
    async def test_fastapi_server_starts_even_without_whatsapp(self):
        """The HTTP server (always-on /health) must start regardless of WhatsApp config."""
        with (
            patch.object(settings, "whatsapp_token", ""),
            patch.object(settings, "whatsapp_phone_id", ""),
            patch("src.main.init_beanie_models", new=AsyncMock()),
            patch("src.main.run_bot", new=AsyncMock()) as mock_run_bot,
            patch("src.main.serve_fastapi", new=AsyncMock()) as mock_serve_fastapi,
        ):
            await _async_main()

        mock_run_bot.assert_awaited_once()
        mock_serve_fastapi.assert_awaited_once()
