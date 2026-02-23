"""Tests for bot sender rejection guard."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.ext import ApplicationHandlerStop

from src.telegram.chat_params import is_bot_sender
from src.telegram.setup import _reject_bot_senders


def _make_update(*, is_bot: bool | None) -> MagicMock:
    update = MagicMock()
    if is_bot is None:
        update.effective_user = None
    else:
        update.effective_user = MagicMock()
        update.effective_user.is_bot = is_bot
        update.effective_user.id = 999
    return update


class TestIsBotSender:
    def test_returns_true_for_bot(self):
        assert is_bot_sender(_make_update(is_bot=True)) is True

    def test_returns_false_for_human(self):
        assert is_bot_sender(_make_update(is_bot=False)) is False

    def test_returns_false_when_no_user(self):
        assert is_bot_sender(_make_update(is_bot=None)) is False


class TestRejectBotSenders:
    async def test_raises_stop_for_bot(self):
        update = _make_update(is_bot=True)
        context = MagicMock()
        context.bot = AsyncMock()

        with pytest.raises(ApplicationHandlerStop):
            await _reject_bot_senders(update, context)

    async def test_passes_for_human(self):
        update = _make_update(is_bot=False)
        context = MagicMock()
        context.bot = AsyncMock()

        # Must not raise
        await _reject_bot_senders(update, context)

    async def test_passes_when_no_user(self):
        update = _make_update(is_bot=None)
        context = MagicMock()
        context.bot = AsyncMock()

        # Must not raise (e.g., channel post with no user)
        await _reject_bot_senders(update, context)
