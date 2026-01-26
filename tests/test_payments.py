"""Tests for Telegram Stars payment flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from src import const
from src.telegram.payments import (
    balance_command,
    buy_command,
    handle_pre_checkout,
    handle_successful_payment,
)


class TestBuyCommand:
    async def test_buy_sends_invoice(self, mock_private_update, mock_context):
        mock_private_update.effective_user.id = 111
        mock_context.bot.send_invoice = AsyncMock()

        await buy_command(mock_private_update, mock_context)

        mock_context.bot.send_invoice.assert_called_once()
        call_kwargs = mock_context.bot.send_invoice.call_args[1]
        assert call_kwargs["currency"] == const.TELEGRAM_STARS_CURRENCY


class TestPreCheckout:
    async def test_pre_checkout_approved(self, mock_private_update, mock_context):
        query = MagicMock()
        query.answer = AsyncMock()
        query.invoice_payload = "buy_credits"
        mock_private_update.pre_checkout_query = query

        await handle_pre_checkout(mock_private_update, mock_context)

        query.answer.assert_called_once_with(ok=True)


class TestSuccessfulPayment:
    async def test_credits_added_on_payment(self, mock_private_update, mock_context):
        mock_private_update.effective_user.id = 111
        mock_private_update.message.successful_payment = MagicMock()
        mock_private_update.message.successful_payment.total_amount = 5

        with patch("src.telegram.payments.settings") as mock_settings:
            mock_settings.credits_per_star = 1
            await handle_successful_payment(mock_private_update, mock_context)

        mock_context.bot.send_message.assert_called_once()


class TestBalanceCommand:
    async def test_balance_shows_credits(self, mock_private_update, mock_context):
        mock_private_update.effective_user.id = 111

        await balance_command(mock_private_update, mock_context)

        mock_context.bot.send_message.assert_called_once()
