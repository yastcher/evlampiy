"""Tests for Telegram Stars payment flow."""

from unittest.mock import AsyncMock, MagicMock, patch

from src import const
from src.alerts import check_and_send_alerts
from src.credits import add_credits, get_total_credits, increment_payment_stats
from src.telegram.payments import (
    balance_command,
    buy_command,
    buy_package_callback,
    handle_pre_checkout,
    handle_successful_payment,
)


class TestPaymentFlow:
    """Integration test for complete payment flow with real DB."""

    async def test_complete_payment_flow(self, mock_private_update, mock_context):
        """Complete flow: buy → select package → pre_checkout → payment → balance."""
        user_id = "222"
        mock_private_update.effective_user.id = 222
        mock_context.bot.send_invoice = AsyncMock()
        mock_context.bot.send_message = AsyncMock()

        # 1. User starts purchase with /buy — sees package keyboard
        await buy_command(mock_private_update, mock_context)
        mock_private_update.message.reply_text.assert_called_once()
        call_kwargs = mock_private_update.message.reply_text.call_args
        keyboard = call_kwargs.kwargs["reply_markup"].inline_keyboard
        assert len(keyboard) == 4

        # 2. User selects Medium package (index 1)
        query = MagicMock()
        query.answer = AsyncMock()
        query.data = "buy_pkg_1"
        mock_private_update.callback_query = query

        await buy_package_callback(mock_private_update, mock_context)
        mock_context.bot.send_invoice.assert_called_once()
        invoice_kwargs = mock_context.bot.send_invoice.call_args[1]
        assert invoice_kwargs["currency"] == const.TELEGRAM_STARS_CURRENCY
        assert invoice_kwargs["payload"] == "buy_tokens_1"

        # 3. Pre-checkout query is approved
        checkout_query = MagicMock()
        checkout_query.answer = AsyncMock()
        mock_private_update.pre_checkout_query = checkout_query
        await handle_pre_checkout(mock_private_update, mock_context)
        checkout_query.answer.assert_called_once_with(ok=True)

        # 4. Payment succeeds - tokens added to real DB
        mock_private_update.message.successful_payment = MagicMock()
        mock_private_update.message.successful_payment.total_amount = 25
        mock_private_update.message.successful_payment.invoice_payload = "buy_tokens_1"

        initial_balance = await get_total_credits(user_id)
        await handle_successful_payment(mock_private_update, mock_context)

        # Medium package = 30 tokens
        new_balance = await get_total_credits(user_id)
        assert new_balance == initial_balance + 30

        # 5. User checks balance
        mock_context.bot.send_message.reset_mock()
        await balance_command(mock_private_update, mock_context)
        mock_context.bot.send_message.assert_called_once()
        message_text = mock_context.bot.send_message.call_args[1]["text"]
        assert "30" in message_text or str(new_balance) in message_text


class TestBuyCommand:
    """Test /buy command shows packages."""

    async def test_buy_shows_package_keyboard(self, mock_private_update, mock_context):
        """Buy command shows inline keyboard with 4 packages."""
        mock_private_update.effective_user.id = 111
        await buy_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_args = mock_private_update.message.reply_text.call_args
        keyboard = call_args.kwargs["reply_markup"].inline_keyboard
        assert len(keyboard) == 4

        # Verify callback data
        for i, row in enumerate(keyboard):
            assert row[0].callback_data == f"buy_pkg_{i}"


class TestBuyPackageCallback:
    """Test package selection callback."""

    async def test_sends_invoice_for_selected_package(self, mock_private_update, mock_context):
        """Selecting a package sends the correct invoice."""
        query = MagicMock()
        query.answer = AsyncMock()
        query.data = "buy_pkg_2"  # Large package
        mock_private_update.callback_query = query
        mock_context.bot.send_invoice = AsyncMock()

        await buy_package_callback(mock_private_update, mock_context)

        mock_context.bot.send_invoice.assert_called_once()
        kwargs = mock_context.bot.send_invoice.call_args[1]
        assert kwargs["currency"] == const.TELEGRAM_STARS_CURRENCY
        assert kwargs["payload"] == "buy_tokens_2"
        assert "65" in kwargs["description"]  # 65 tokens


class TestPreCheckout:
    """Test pre-checkout handler."""

    async def test_pre_checkout_approved(self, mock_private_update, mock_context):
        """Pre-checkout query is approved."""
        query = MagicMock()
        query.answer = AsyncMock()
        mock_private_update.pre_checkout_query = query

        await handle_pre_checkout(mock_private_update, mock_context)
        query.answer.assert_called_once_with(ok=True)


class TestSuccessfulPayment:
    """Test successful payment handler with real DB."""

    async def test_tokens_added_on_package_payment(self, mock_private_update, mock_context):
        """Tokens from selected package are added to user balance."""
        user_id = "333"
        mock_private_update.effective_user.id = 333
        mock_private_update.message.successful_payment = MagicMock()
        mock_private_update.message.successful_payment.total_amount = 50
        mock_private_update.message.successful_payment.invoice_payload = "buy_tokens_2"

        initial = await get_total_credits(user_id)
        await handle_successful_payment(mock_private_update, mock_context)

        # Large package = 65 tokens
        assert await get_total_credits(user_id) == initial + 65

    async def test_legacy_payment_fallback(self, mock_private_update, mock_context):
        """Legacy payload (no buy_tokens_ prefix) uses total_amount as tokens."""
        mock_private_update.effective_user.id = 999
        user_id = str(mock_private_update.effective_user.id)
        mock_private_update.message.successful_payment = MagicMock()
        mock_private_update.message.successful_payment.total_amount = 10
        mock_private_update.message.successful_payment.invoice_payload = "buy_credits"

        initial = await get_total_credits(user_id)
        await handle_successful_payment(mock_private_update, mock_context)

        assert await get_total_credits(user_id) == initial + 10


class TestBalanceCommand:
    """Test /balance command with real DB."""

    async def test_balance_shows_detailed_info(self, mock_private_update, mock_context):
        """Balance command shows free/purchased split."""
        user_id = "444"
        mock_private_update.effective_user.id = 444
        mock_context.bot.send_message = AsyncMock()

        await add_credits(user_id, 50)
        await balance_command(mock_private_update, mock_context)

        mock_context.bot.send_message.assert_called_once()
        text = mock_context.bot.send_message.call_args[1]["text"]
        assert "60" in text  # 10 free + 50 purchased
        assert "50" in text  # purchased
        assert "10" in text  # free


class TestMilestoneAlerts:
    """Test milestone alerts on payment."""

    async def test_milestone_triggers_on_bulk_purchase(self, mock_private_update, mock_context):
        """Milestone alert triggers when buying crossing threshold."""
        credits_for_10_dollars = int(10 / const.STAR_TO_DOLLAR) + 1

        await increment_payment_stats(credits_for_10_dollars)

        alerts_sent = []

        async def capture_alert(bot, message):
            alerts_sent.append(message)

        with (
            patch("src.alerts.send_admin_alert", capture_alert),
            patch("src.alerts.settings") as mock_settings,
        ):
            mock_settings.admin_user_ids = ["123"]
            mock_settings.wit_free_monthly_limit = 500
            await check_and_send_alerts(mock_context.bot, credits_just_sold=credits_for_10_dollars)

        milestone_alerts = [a for a in alerts_sent if "$10" in a]
        assert len(milestone_alerts) == 1
