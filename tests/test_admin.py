"""Tests for admin role and statistics."""

from unittest.mock import patch

import pytest

from src.config import settings
from src.dto import AlertState, MonthlyStats, UserCredits, WitUsageStats

pytestmark = [pytest.mark.asyncio]


class TestAdminRole:
    async def test_admin_has_unlimited_access(self):
        """Admin bypasses credit checks."""
        from src.credits import has_unlimited_access

        admin_id = 999
        with patch.object(settings, "admin_user_ids", {admin_id}):
            assert has_unlimited_access(admin_id) is True

    async def test_vip_has_unlimited_access(self):
        """VIP also bypasses credit checks."""
        from src.credits import has_unlimited_access

        vip_id = 888
        with (
            patch.object(settings, "vip_user_ids", {vip_id}),
            patch.object(settings, "admin_user_ids", set()),
        ):
            assert has_unlimited_access(vip_id) is True

    async def test_regular_user_limited(self):
        """Regular user does not have unlimited access."""
        from src.credits import has_unlimited_access

        user_id = 123
        with (
            patch.object(settings, "admin_user_ids", set()),
            patch.object(settings, "vip_user_ids", set()),
        ):
            assert has_unlimited_access(user_id) is False

    async def test_is_admin_user(self):
        """Test is_admin_user function."""
        from src.credits import is_admin_user

        admin_id = 999
        regular_id = 123
        with patch.object(settings, "admin_user_ids", {admin_id}):
            assert is_admin_user(admin_id) is True
            assert is_admin_user(regular_id) is False


class TestStatsCommand:
    async def test_admin_sees_stats(self, mock_private_update, mock_context):
        """Admin can view system stats."""
        from src.telegram.handlers import stats_command

        admin_id = 999
        mock_private_update.effective_user.id = admin_id

        with patch.object(settings, "admin_user_ids", {admin_id}):
            await stats_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()

    async def test_non_admin_ignored(self, mock_private_update, mock_context):
        """Non-admin cannot view system stats."""
        from src.telegram.handlers import stats_command

        mock_private_update.effective_user.id = 123

        with patch.object(settings, "admin_user_ids", set()):
            await stats_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_not_called()


class TestMyStatsCommand:
    async def test_user_sees_own_stats(self, mock_private_update, mock_context):
        """User can view their own stats."""
        from src.credits import add_credits
        from src.telegram.handlers import mystats_command

        user_id = 123
        mock_private_update.effective_user.id = user_id

        await add_credits(user_id, 50)

        await mystats_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "50" in call_text

    async def test_mystats_shows_tier(self, mock_private_update, mock_context):
        """Personal stats show user tier."""
        from src.credits import add_credits
        from src.telegram.handlers import mystats_command

        user_id = 456
        mock_private_update.effective_user.id = user_id

        await add_credits(user_id, 10)

        await mystats_command(mock_private_update, mock_context)

        call_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "paid" in call_text.lower()


class TestAlerts:
    async def test_first_payment_alert_sent(self, mock_context):
        """First payment triggers celebration alert."""
        from src.alerts import check_and_send_alerts
        from src.credits import current_month_key

        month = current_month_key()
        await MonthlyStats(month_key=month, total_payments=1, total_credits_sold=5).insert()

        with patch.object(settings, "admin_user_ids", {999}):
            await check_and_send_alerts(mock_context.bot)

        mock_context.bot.send_message.assert_called()
        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "First payment" in call_text

    async def test_wit_warning_at_80_percent(self, mock_context):
        """Wit.ai warning sent at 80% usage."""
        from src.alerts import check_and_send_alerts
        from src.credits import current_month_key

        month = current_month_key()
        await WitUsageStats(month_key=month, request_count=450).insert()

        with (
            patch.object(settings, "admin_user_ids", {999}),
            patch.object(settings, "wit_free_monthly_limit", 500),
        ):
            await check_and_send_alerts(mock_context.bot)

        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "Warning" in call_text

    async def test_wit_critical_at_95_percent(self, mock_context):
        """Wit.ai critical alert sent at 95% usage."""
        from src.alerts import check_and_send_alerts
        from src.credits import current_month_key

        month = current_month_key()
        await WitUsageStats(month_key=month, request_count=480).insert()

        with (
            patch.object(settings, "admin_user_ids", {999}),
            patch.object(settings, "wit_free_monthly_limit", 500),
        ):
            await check_and_send_alerts(mock_context.bot)

        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "CRITICAL" in call_text

    async def test_alert_not_duplicated(self, mock_context):
        """Same alert not sent twice in same month."""
        from src.alerts import check_and_send_alerts
        from src.credits import current_month_key

        month = current_month_key()
        await WitUsageStats(month_key=month, request_count=450).insert()
        await AlertState(alert_type="wit_80", month_key=month).insert()

        with (
            patch.object(settings, "admin_user_ids", {999}),
            patch.object(settings, "wit_free_monthly_limit", 500),
        ):
            await check_and_send_alerts(mock_context.bot)

        mock_context.bot.send_message.assert_not_called()


class TestUserStatsTracking:
    async def test_track_user_transcription(self):
        """User transcription count is tracked."""
        from src.credits import add_credits, increment_user_stats

        user_id = 123
        await add_credits(user_id, 10)
        await increment_user_stats(user_id, audio_seconds=30)

        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_transcriptions == 1
        assert record.total_audio_seconds == 30

    async def test_track_credits_spent(self):
        """Track credits spent by user."""
        from src.credits import add_credits, deduct_credits

        user_id = 456
        await add_credits(user_id, 50)
        await deduct_credits(user_id, 10)

        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_credits_spent == 10

    async def test_track_credits_purchased(self):
        """Track credits purchased by user."""
        from src.credits import add_credits

        user_id = 789
        await add_credits(user_id, 100)

        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_credits_purchased == 100
