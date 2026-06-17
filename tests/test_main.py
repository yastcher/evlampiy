"""Entrypoint wiring and subsystem supervision (`src.main`)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.config import settings
from src.main import _async_main, _supervise


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


class TestSupervise:
    async def test_restarts_subsystem_after_crash(self):
        """A crashing subsystem is restarted instead of taking the process down."""
        calls = 0

        async def flaky():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("boom")

        with patch("src.main._SUPERVISOR_INITIAL_BACKOFF_SECONDS", 0):
            await _supervise("test", flaky)

        assert calls == 2  # crashed once, restarted, then exited cleanly

    async def test_clean_exit_is_not_restarted(self):
        calls = 0

        async def once():
            nonlocal calls
            calls += 1

        await _supervise("test", once)

        assert calls == 1

    async def test_cancellation_propagates(self):
        async def hang():
            await asyncio.Event().wait()

        task = asyncio.create_task(_supervise("test", hang))
        await asyncio.sleep(0)  # let the supervised coroutine start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
