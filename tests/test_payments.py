"""Tests for Telegram Stars payment flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from src import const
from src.credits import get_credits
from src.telegram.payments import (
    balance_command,
    buy_command,
    handle_pre_checkout,
    handle_successful_payment,
)


class TestPaymentFlow:
    """Integration test for complete payment flow with real DB."""

    async def test_complete_payment_flow(self, mock_private_update, mock_context):
        """Complete payment flow: buy_command → pre_checkout → payment → balance."""
        user_id = "222"
        mock_private_update.effective_user.id = 222
        mock_context.bot.send_invoice = AsyncMock()
        mock_context.bot.send_message = AsyncMock()

        # 1. User starts purchase with /buy
        await buy_command(mock_private_update, mock_context)

        mock_context.bot.send_invoice.assert_called_once()
        call_kwargs = mock_context.bot.send_invoice.call_args[1]
        assert call_kwargs["currency"] == const.TELEGRAM_STARS_CURRENCY

        # 2. Pre-checkout query is approved
        query = MagicMock()
        query.answer = AsyncMock()
        query.invoice_payload = "buy_credits"
        mock_private_update.pre_checkout_query = query

        await handle_pre_checkout(mock_private_update, mock_context)
        query.answer.assert_called_once_with(ok=True)

        # 3. Payment succeeds - credits added to real DB
        mock_private_update.message.successful_payment = MagicMock()
        mock_private_update.message.successful_payment.total_amount = 5

        initial_balance = await get_credits(user_id)

        with patch("src.telegram.payments.settings") as mock_settings:
            mock_settings.credits_per_star = 2  # 5 stars * 2 = 10 credits
            await handle_successful_payment(mock_private_update, mock_context)

        # Verify credits were added to real DB
        new_balance = await get_credits(user_id)
        assert new_balance == initial_balance + 10

        # 4. User checks balance with /balance
        mock_context.bot.send_message.reset_mock()
        await balance_command(mock_private_update, mock_context)

        mock_context.bot.send_message.assert_called_once()
        message_text = mock_context.bot.send_message.call_args[1]["text"]
        assert "10" in message_text or str(new_balance) in message_text


class TestBuyCommand:
    """Test /buy command."""

    async def test_buy_sends_invoice(self, mock_private_update, mock_context):
        """Buy command sends Telegram Stars invoice."""
        mock_private_update.effective_user.id = 111
        mock_context.bot.send_invoice = AsyncMock()

        await buy_command(mock_private_update, mock_context)

        mock_context.bot.send_invoice.assert_called_once()
        call_kwargs = mock_context.bot.send_invoice.call_args[1]
        assert call_kwargs["currency"] == const.TELEGRAM_STARS_CURRENCY


class TestPreCheckout:
    """Test pre-checkout handler."""

    async def test_pre_checkout_approved(self, mock_private_update, mock_context):
        """Pre-checkout query is approved."""
        query = MagicMock()
        query.answer = AsyncMock()
        query.invoice_payload = "buy_credits"
        mock_private_update.pre_checkout_query = query

        await handle_pre_checkout(mock_private_update, mock_context)

        query.answer.assert_called_once_with(ok=True)


class TestSuccessfulPayment:
    """Test successful payment handler with real DB."""

    async def test_credits_added_on_payment(self, mock_private_update, mock_context):
        """Credits are added to user balance in real DB."""
        user_id = "333"
        mock_private_update.effective_user.id = 333
        mock_private_update.message.successful_payment = MagicMock()
        mock_private_update.message.successful_payment.total_amount = 10  # 10 stars

        initial_balance = await get_credits(user_id)

        with patch("src.telegram.payments.settings") as mock_settings:
            mock_settings.credits_per_star = 3  # 10 stars * 3 = 30 credits
            await handle_successful_payment(mock_private_update, mock_context)

        # Verify credits were added to real DB
        new_balance = await get_credits(user_id)
        assert new_balance == initial_balance + 30


class TestBalanceCommand:
    """Test /balance command with real DB."""

    async def test_balance_shows_credits(self, mock_private_update, mock_context):
        """Balance command shows user's credits from real DB."""
        from src.credits import add_credits

        user_id = "444"
        mock_private_update.effective_user.id = 444
        mock_context.bot.send_message = AsyncMock()

        # Add some credits to real DB
        await add_credits(user_id, 50)

        await balance_command(mock_private_update, mock_context)

        mock_context.bot.send_message.assert_called_once()
        message_text = mock_context.bot.send_message.call_args[1]["text"]
        assert "50" in message_text


class TestMilestoneAlerts:
    """Test milestone alerts on payment."""

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
