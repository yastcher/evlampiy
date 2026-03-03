"""Tests for bot sender rejection guard."""

import pytest
from telegram.ext import ApplicationHandlerStop

from src.telegram.chat_params import is_bot_sender
from src.telegram.setup import _reject_bot_senders


class TestIsBotSender:
    def test_returns_true_for_bot(self, make_update_factory):
        assert is_bot_sender(make_update_factory(is_bot=True)) is True

    def test_returns_false_for_human(self, make_update_factory):
        assert is_bot_sender(make_update_factory(is_bot=False)) is False

    def test_returns_false_when_no_user(self, make_update_factory):
        assert is_bot_sender(make_update_factory(is_bot=None)) is False


class TestRejectBotSenders:
    async def test_raises_stop_for_bot(self, make_update_factory, mock_context):
        update = make_update_factory(is_bot=True)

        with pytest.raises(ApplicationHandlerStop):
            await _reject_bot_senders(update, mock_context)

    async def test_passes_for_human(self, make_update_factory, mock_context):
        update = make_update_factory(is_bot=False)

        # Must not raise
        await _reject_bot_senders(update, mock_context)

    async def test_passes_when_no_user(self, make_update_factory, mock_context):
        update = make_update_factory(is_bot=None)

        # Must not raise (e.g., channel post with no user)
        await _reject_bot_senders(update, mock_context)
