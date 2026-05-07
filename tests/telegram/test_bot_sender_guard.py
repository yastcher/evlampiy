"""Tests for bot sender rejection middleware."""

from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Message, Update

from src.telegram.chat_params import is_bot_sender
from src.telegram.setup import BotSenderRejectMiddleware


class TestIsBotSender:
    def test_returns_true_for_bot(self, make_update_factory):
        assert is_bot_sender(make_update_factory(is_bot=True)) is True

    def test_returns_false_for_human(self, make_update_factory):
        assert is_bot_sender(make_update_factory(is_bot=False)) is False

    def test_returns_false_when_no_user(self, make_update_factory):
        assert is_bot_sender(make_update_factory(is_bot=None)) is False


def _build_update(*, is_bot: bool | None) -> MagicMock:
    inner = MagicMock(spec=Message)
    if is_bot is None:
        inner.from_user = None
    else:
        inner.from_user = MagicMock()
        inner.from_user.is_bot = is_bot
        inner.from_user.id = 999
    update = MagicMock(spec=Update)
    update.event = inner
    return update


class TestBotSenderRejectMiddleware:
    async def test_drops_bot_update(self):
        middleware = BotSenderRejectMiddleware()
        downstream = AsyncMock(return_value="handled")
        result = await middleware(downstream, _build_update(is_bot=True), {})
        assert result is None
        downstream.assert_not_called()

    async def test_passes_human_update(self):
        middleware = BotSenderRejectMiddleware()
        downstream = AsyncMock(return_value="handled")
        result = await middleware(downstream, _build_update(is_bot=False), {})
        assert result == "handled"
        downstream.assert_called_once()

    async def test_passes_when_no_user(self):
        middleware = BotSenderRejectMiddleware()
        downstream = AsyncMock(return_value="handled")
        result = await middleware(downstream, _build_update(is_bot=None), {})
        assert result == "handled"
        downstream.assert_called_once()
