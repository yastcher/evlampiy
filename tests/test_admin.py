"""Tests for admin role and statistics."""

from unittest.mock import patch

from src.alerts import check_and_send_alerts
from src.config import settings
from src.credits import (
    add_credits,
    current_month_key,
    deduct_credits,
    has_unlimited_access,
    increment_payment_stats,
    increment_transcription_stats,
    increment_user_stats,
    is_admin_user,
    record_groq_usage,
)
from src.dto import AlertState, MonthlyStats, UserCredits, WitUsageStats
from src.telegram.handlers import mystats_command, stats_command


class TestAdminRole:
    async def test_admin_has_unlimited_access(self):
        """Admin bypasses credit checks."""
        admin_id = "999"
        with patch.object(settings, "admin_user_ids_raw", "999"):
            assert has_unlimited_access(admin_id) is True

    async def test_vip_has_unlimited_access(self):
        """VIP also bypasses credit checks."""
        vip_id = "888"
        with (
            patch.object(settings, "vip_user_ids_raw", "888"),
            patch.object(settings, "admin_user_ids_raw", ""),
        ):
            assert has_unlimited_access(vip_id) is True

    async def test_regular_user_limited(self):
        """Regular user does not have unlimited access."""
        user_id = "123"
        with (
            patch.object(settings, "admin_user_ids_raw", ""),
            patch.object(settings, "vip_user_ids_raw", ""),
        ):
            assert has_unlimited_access(user_id) is False

    async def test_is_admin_user(self):
        """Test is_admin_user function."""
        admin_id = "999"
        regular_id = "123"
        with patch.object(settings, "admin_user_ids_raw", "999"):
            assert is_admin_user(admin_id) is True
            assert is_admin_user(regular_id) is False


class TestStatsCommand:
    async def test_admin_sees_stats(self, mock_private_update, mock_context):
        """Admin can view system stats with real data from DB."""
        admin_id = 999
        mock_private_update.effective_user.id = admin_id

        await increment_transcription_stats()
        await increment_transcription_stats()
        await increment_transcription_stats()
        await increment_payment_stats(50)

        with patch.object(settings, "admin_user_ids_raw", "999"):
            await stats_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_text = mock_private_update.message.reply_text.call_args[0][0]
        # Verify real stats are shown in response
        assert "3" in call_text  # transcriptions count
        assert "50" in call_text  # credits sold

    async def test_non_admin_ignored(self, mock_private_update, mock_context):
        """Non-admin cannot view system stats."""
        mock_private_update.effective_user.id = 123

        with patch.object(settings, "admin_user_ids_raw", ""):
            await stats_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_not_called()


class TestMyStatsCommand:
    async def test_user_sees_own_stats(self, mock_private_update, mock_context):
        """User can view their own stats."""
        user_id = "123"
        mock_private_update.effective_user.id = 123

        await add_credits(user_id, 50)

        await mystats_command(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        call_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "50" in call_text

    async def test_mystats_shows_tier(self, mock_private_update, mock_context):
        """Personal stats show user tier."""
        user_id = "456"
        mock_private_update.effective_user.id = 456

        await add_credits(user_id, 10)

        await mystats_command(mock_private_update, mock_context)

        call_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "paid" in call_text.lower()


class TestAlerts:
    async def test_first_payment_alert_sent(self, mock_context):
        """First payment triggers celebration alert."""
        month = current_month_key()
        await MonthlyStats(month_key=month, total_payments=1, total_credits_sold=5).insert()

        with patch.object(settings, "admin_user_ids_raw", "999"):
            await check_and_send_alerts(mock_context.bot)

        mock_context.bot.send_message.assert_called()
        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "First payment" in call_text

    async def test_wit_warning_at_80_percent(self, mock_context):
        """Wit.ai warning sent at 80% usage."""
        month = current_month_key()
        await WitUsageStats(month_key=month, request_count=450).insert()

        with (
            patch.object(settings, "admin_user_ids_raw", "999"),
            patch.object(settings, "wit_free_monthly_limit", 500),
        ):
            await check_and_send_alerts(mock_context.bot)

        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "Warning" in call_text

    async def test_wit_critical_at_95_percent(self, mock_context):
        """Wit.ai critical alert sent at 95% usage."""
        month = current_month_key()
        await WitUsageStats(month_key=month, request_count=480).insert()

        with (
            patch.object(settings, "admin_user_ids_raw", "999"),
            patch.object(settings, "wit_free_monthly_limit", 500),
        ):
            await check_and_send_alerts(mock_context.bot)

        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "CRITICAL" in call_text

    async def test_alert_not_duplicated(self, mock_context):
        """Same alert not sent twice in same month."""
        month = current_month_key()
        await WitUsageStats(month_key=month, request_count=450).insert()
        await AlertState(alert_type="wit_80", month_key=month).insert()

        with (
            patch.object(settings, "admin_user_ids_raw", "999"),
            patch.object(settings, "wit_free_monthly_limit", 500),
        ):
            await check_and_send_alerts(mock_context.bot)

        mock_context.bot.send_message.assert_not_called()


class TestUserStatsTracking:
    async def test_increment_user_stats_new_user(self):
        """Increment stats creates record for new user."""
        user_id = "new_stats_user_999"

        # Ensure user doesn't exist
        existing = await UserCredits.find_one(UserCredits.user_id == user_id)
        if existing:
            await existing.delete()

        await increment_user_stats(user_id, audio_seconds=30)

        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record is not None
        assert record.total_transcriptions == 1
        assert record.total_audio_seconds == 30

    async def test_record_groq_usage(self):
        """Groq audio usage is recorded in monthly stats."""
        await record_groq_usage(45)

        month_key = current_month_key()
        stats = await MonthlyStats.find_one(MonthlyStats.month_key == month_key)
        assert stats is not None
        assert stats.groq_audio_seconds >= 45

    async def test_complete_user_stats_flow(self):
        """Test complete user stats tracking flow."""
        user_id = "777888"

        # 1. Purchase credits - track total_credits_purchased
        await add_credits(user_id, 100)
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_credits_purchased == 100
        assert record.credits == 100

        # 2. Add more credits - accumulates
        await add_credits(user_id, 50)
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_credits_purchased == 150
        assert record.credits == 150

        # 3. Spend credits - track total_credits_spent
        await deduct_credits(user_id, 30)
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_credits_spent == 30
        assert record.credits == 120

        # 4. Track transcription stats
        await increment_user_stats(user_id, audio_seconds=45)
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_transcriptions == 1
        assert record.total_audio_seconds == 45

        # 5. Multiple transcriptions accumulate
        await increment_user_stats(user_id, audio_seconds=60)
        await increment_user_stats(user_id, audio_seconds=30)
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_transcriptions == 3
        assert record.total_audio_seconds == 135

        # 6. Credits unchanged by stats tracking
        assert record.credits == 120
