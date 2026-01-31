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


class TestMilestoneAlerts:
    async def test_milestone_triggers_on_bulk_purchase(self, mock_private_update, mock_context):
        """Milestone alert triggers when buying multiple credits at once crossing threshold."""
        from src import const
        from src.alerts import check_and_send_alerts
        from src.credits import increment_payment_stats

        credits_for_10_dollars = int(10 / const.STAR_TO_DOLLAR) + 1

        await increment_payment_stats(credits_for_10_dollars)

        alerts_sent = []

        async def capture_alert(bot, message):
            alerts_sent.append(message)

        with patch("src.alerts.send_admin_alert", capture_alert):
            with patch("src.alerts.settings") as mock_settings:
                mock_settings.admin_user_ids = ["123"]
                mock_settings.wit_free_monthly_limit = 500
                await check_and_send_alerts(mock_context.bot, credits_just_sold=credits_for_10_dollars)

        milestone_alerts = [a for a in alerts_sent if "$10" in a]
        assert len(milestone_alerts) == 1
