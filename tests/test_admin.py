"""Tests for admin role, statistics, and user management commands."""

from unittest.mock import patch

from src import const
from src.alerts import check_and_send_alerts
from src.config import settings
from src.credits import (
    add_credits,
    admin_add_credits,
    current_month_key,
    deduct_credits,
    get_total_credits,
    has_unlimited_access,
    has_unlimited_voice_access,
    increment_payment_stats,
    increment_transcription_stats,
    increment_user_stats,
    is_admin_user,
    is_blocked_user,
    is_tester_user,
    is_vip_user,
    record_groq_usage,
)
from src.dto import AlertState, MonthlyStats, UserCredits, UserTier, WitUsageStats
from src.mongo import add_user_role, get_bot_config, get_users_by_role, remove_user_role
from src.telegram.admin import (
    _build_providers_panel,
    add_credits_command,
    add_tester_command,
    add_vip_command,
    admin_callback_router,
    admin_hub,
    block_command,
    remove_tester_command,
    remove_vip_command,
    unblock_command,
)
from src.telegram.handlers import mystats_command, stats_command


class TestAdminRole:
    async def test_admin_has_unlimited_access(self, admin_auth):
        """Admin bypasses credit checks."""
        assert await has_unlimited_access("999") is True

    async def test_vip_has_unlimited_access(self):
        """VIP from DB bypasses credit checks."""
        vip_id = "888"
        await add_user_role(vip_id, const.ROLE_VIP, "admin")
        with patch.object(settings, "admin_user_ids_raw", ""):
            assert await has_unlimited_access(vip_id) is True

    async def test_vip_env_fallback(self):
        """VIP from env var still works."""
        vip_id = "777"
        with (
            patch.object(settings, "vip_user_ids_raw", "777"),
            patch.object(settings, "admin_user_ids_raw", ""),
        ):
            assert await is_vip_user(vip_id) is True
            assert await has_unlimited_access(vip_id) is True

    async def test_regular_user_limited(self):
        """Regular user does not have unlimited access."""
        user_id = "123"
        with (
            patch.object(settings, "admin_user_ids_raw", ""),
            patch.object(settings, "vip_user_ids_raw", ""),
        ):
            assert await has_unlimited_access(user_id) is False

    async def test_is_admin_user(self, admin_auth):
        """Test is_admin_user function."""
        assert is_admin_user("999") is True
        assert is_admin_user("123") is False


class TestTesterRole:
    async def test_tester_has_unlimited_voice(self):
        """Tester has unlimited voice access."""
        tester_id = "555"
        await add_user_role(tester_id, const.ROLE_TESTER, "admin")
        with (
            patch.object(settings, "admin_user_ids_raw", ""),
            patch.object(settings, "vip_user_ids_raw", ""),
        ):
            assert await is_tester_user(tester_id) is True
            assert await has_unlimited_voice_access(tester_id) is True
            assert await has_unlimited_access(tester_id) is False

    async def test_tester_not_unlimited_access(self):
        """Tester does not have full unlimited access (GPT/categorization)."""
        tester_id = "556"
        await add_user_role(tester_id, const.ROLE_TESTER, "admin")
        with (
            patch.object(settings, "admin_user_ids_raw", ""),
            patch.object(settings, "vip_user_ids_raw", ""),
        ):
            assert await has_unlimited_access(tester_id) is False

    async def test_admin_add_credits_preserves_tier(self):
        """Admin top-up does not change tier to PAID."""
        user_id = "557"
        balance = await admin_add_credits(user_id, 50)
        assert balance == 50
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.tier == UserTier.FREE

    async def test_admin_add_credits_to_existing_user(self):
        """Admin top-up accumulates for existing user."""
        user_id = "558"
        await admin_add_credits(user_id, 20)
        balance = await admin_add_credits(user_id, 30)
        assert balance == 50
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.purchased_credits == 50

    async def test_vip_has_unlimited_voice_access(self):
        """VIP from DB has unlimited voice access."""
        vip_id = "889"
        await add_user_role(vip_id, const.ROLE_VIP, "admin")
        with (
            patch.object(settings, "admin_user_ids_raw", ""),
            patch.object(settings, "vip_user_ids_raw", ""),
        ):
            assert await has_unlimited_voice_access(vip_id) is True


class TestUserRoleCrud:
    async def test_add_and_list_roles(self):
        """Add users to roles and list them."""
        await add_user_role("100", const.ROLE_VIP, "admin")
        await add_user_role("200", const.ROLE_VIP, "admin")
        await add_user_role("300", const.ROLE_TESTER, "admin")

        vips = await get_users_by_role(const.ROLE_VIP)
        assert set(vips) == {"100", "200"}

        testers = await get_users_by_role(const.ROLE_TESTER)
        assert testers == ["300"]

    async def test_remove_role(self):
        """Remove a role from a user."""
        await add_user_role("100", const.ROLE_VIP, "admin")
        removed = await remove_user_role("100", const.ROLE_VIP)
        assert removed is True

        vips = await get_users_by_role(const.ROLE_VIP)
        assert vips == []

    async def test_remove_nonexistent_role(self):
        """Removing a non-existent role returns False."""
        removed = await remove_user_role("999", const.ROLE_VIP)
        assert removed is False

    async def test_add_role_idempotent(self):
        """Adding the same role twice does not duplicate."""
        await add_user_role("100", const.ROLE_VIP, "admin")
        await add_user_role("100", const.ROLE_VIP, "admin")

        vips = await get_users_by_role(const.ROLE_VIP)
        assert vips == ["100"]


class TestAdminCommands:
    async def test_admin_hub_shown_to_admin(self, mock_private_update, mock_context, admin_auth):
        """Admin can see admin hub."""
        mock_private_update.effective_user.id = 999
        await admin_hub(mock_private_update, mock_context)
        mock_private_update.message.reply_text.assert_called_once()

    async def test_admin_hub_hidden_from_non_admin(self, mock_private_update, mock_context):
        """Non-admin cannot see admin hub."""
        mock_private_update.effective_user.id = 123
        with patch.object(settings, "admin_user_ids_raw", ""):
            await admin_hub(mock_private_update, mock_context)
        mock_private_update.message.reply_text.assert_not_called()

    async def test_add_vip_command(self, mock_private_update, mock_context, admin_auth):
        """Admin can add VIP user."""
        mock_private_update.effective_user.id = 999
        mock_context.args = ["12345"]
        await add_vip_command(mock_private_update, mock_context)

        vips = await get_users_by_role(const.ROLE_VIP)
        assert "12345" in vips
        mock_private_update.message.reply_text.assert_called_once()

    async def test_remove_vip_command(self, mock_private_update, mock_context, admin_auth):
        """Admin can remove VIP user."""
        await add_user_role("12345", const.ROLE_VIP, "admin")

        mock_private_update.effective_user.id = 999
        mock_context.args = ["12345"]
        await remove_vip_command(mock_private_update, mock_context)

        vips = await get_users_by_role(const.ROLE_VIP)
        assert "12345" not in vips

    async def test_add_tester_command(self, mock_private_update, mock_context, admin_auth):
        """Admin can add tester."""
        mock_private_update.effective_user.id = 999
        mock_context.args = ["67890"]
        await add_tester_command(mock_private_update, mock_context)

        testers = await get_users_by_role(const.ROLE_TESTER)
        assert "67890" in testers

    async def test_add_credits_command(self, mock_private_update, mock_context, admin_auth):
        """Admin can add credits to a user."""
        mock_private_update.effective_user.id = 999
        mock_context.args = ["12345", "100"]
        await add_credits_command(mock_private_update, mock_context)

        balance = await get_total_credits("12345")
        assert balance == 110  # 10 free + 100 purchased

    async def test_add_credits_invalid_amount(self, mock_private_update, mock_context, admin_auth):
        """Invalid amount shows usage."""
        mock_private_update.effective_user.id = 999
        mock_context.args = ["12345", "abc"]
        await add_credits_command(mock_private_update, mock_context)

        call_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "/add_credits" in call_text

    async def test_remove_tester_command(self, mock_private_update, mock_context, admin_auth):
        """Admin can remove tester."""
        await add_user_role("67890", const.ROLE_TESTER, "admin")

        mock_private_update.effective_user.id = 999
        mock_context.args = ["67890"]
        await remove_tester_command(mock_private_update, mock_context)

        testers = await get_users_by_role(const.ROLE_TESTER)
        assert "67890" not in testers

    async def test_remove_nonexistent_vip(self, mock_private_update, mock_context, admin_auth):
        """Removing non-existent VIP shows not found message."""
        mock_private_update.effective_user.id = 999
        mock_context.args = ["99999"]
        await remove_vip_command(mock_private_update, mock_context)

        call_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "not found" in call_text.lower()

    async def test_admin_callback_vip_list(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Admin callback shows VIP list."""
        await add_user_role("111", const.ROLE_VIP, "admin")

        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_vip"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        mock_callback_query.edit_message_text.assert_called_once()
        call_text = mock_callback_query.edit_message_text.call_args[0][0]
        assert "111" in call_text

    async def test_admin_callback_testers_list(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Admin callback shows tester list."""
        await add_user_role("222", const.ROLE_TESTER, "admin")

        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_testers"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        mock_callback_query.edit_message_text.assert_called_once()
        call_text = mock_callback_query.edit_message_text.call_args[0][0]
        assert "222" in call_text

    async def test_admin_callback_credits_hint(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Admin callback shows credits usage hint."""
        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_credits"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        mock_callback_query.edit_message_text.assert_called_once()
        call_text = mock_callback_query.edit_message_text.call_args[0][0]
        assert "/add_credits" in call_text

    async def test_admin_callback_stats(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Admin stats callback builds stats text and updates message."""
        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_stats"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        mock_callback_query.edit_message_text.assert_called_once()
        call_kwargs = mock_callback_query.edit_message_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"

    async def test_block_command(self, mock_private_update, mock_context, admin_auth):
        """Admin can block a user."""
        mock_private_update.effective_user.id = 999
        mock_context.args = ["12345", "spam"]
        await block_command(mock_private_update, mock_context)

        assert await is_blocked_user("12345") is True
        mock_private_update.message.reply_text.assert_called_once()

    async def test_unblock_command(self, mock_private_update, mock_context, admin_auth):
        """Admin can unblock a user."""
        await add_user_role("12345", "blocked", "admin")

        mock_private_update.effective_user.id = 999
        mock_context.args = ["12345"]
        await unblock_command(mock_private_update, mock_context)

        assert await is_blocked_user("12345") is False
        mock_private_update.message.reply_text.assert_called_once()

    async def test_admin_callback_blocked_list(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Admin callback shows blocked users list."""
        await add_user_role("333", "blocked", "admin")

        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_blocked"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        mock_callback_query.edit_message_text.assert_called_once()
        call_text = mock_callback_query.edit_message_text.call_args[0][0]
        assert "333" in call_text

    async def test_non_admin_commands_blocked(self, mock_private_update, mock_context):
        """Non-admin cannot use admin commands."""
        mock_private_update.effective_user.id = 123
        mock_context.args = ["12345"]
        with patch.object(settings, "admin_user_ids_raw", ""):
            await add_vip_command(mock_private_update, mock_context)
            await remove_vip_command(mock_private_update, mock_context)
            await add_tester_command(mock_private_update, mock_context)
            await remove_tester_command(mock_private_update, mock_context)
        mock_private_update.message.reply_text.assert_not_called()

    async def test_add_vip_no_args(self, mock_private_update, mock_context, admin_auth):
        """Add VIP without args shows usage."""
        mock_private_update.effective_user.id = 999
        mock_context.args = []
        await add_vip_command(mock_private_update, mock_context)

        call_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "/add_vip" in call_text

    async def test_add_credits_negative_amount(self, mock_private_update, mock_context, admin_auth):
        """Negative amount shows usage."""
        mock_private_update.effective_user.id = 999
        mock_context.args = ["12345", "-5"]
        await add_credits_command(mock_private_update, mock_context)

        call_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "/add_credits" in call_text


class TestStatsCommand:
    async def test_admin_sees_stats(self, mock_private_update, mock_context, admin_auth):
        """Admin can view system stats with real data from DB."""
        mock_private_update.effective_user.id = 999

        await increment_transcription_stats()
        await increment_transcription_stats()
        await increment_transcription_stats()
        await increment_payment_stats(50)

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
    async def test_first_payment_alert_sent(self, mock_context, admin_auth):
        """First payment triggers celebration alert."""
        month = current_month_key()
        await MonthlyStats(month_key=month, total_payments=1, total_credits_sold=5).insert()

        await check_and_send_alerts(mock_context.bot)

        mock_context.bot.send_message.assert_called()
        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "First payment" in call_text

    async def test_wit_warning_at_80_percent(self, mock_context, admin_auth):
        """Wit.ai warning sent at 80% usage."""
        month = current_month_key()
        await WitUsageStats(month_key=month, language="ru", request_count=450).insert()

        with patch.object(settings, "wit_free_monthly_limit", 500):
            await check_and_send_alerts(mock_context.bot)

        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "Warning" in call_text

    async def test_wit_critical_at_95_percent(self, mock_context, admin_auth):
        """Wit.ai critical alert sent at 95% usage."""
        month = current_month_key()
        await WitUsageStats(month_key=month, language="ru", request_count=480).insert()

        with patch.object(settings, "wit_free_monthly_limit", 500):
            await check_and_send_alerts(mock_context.bot)

        call_text = mock_context.bot.send_message.call_args.kwargs["text"]
        assert "CRITICAL" in call_text

    async def test_revenue_milestone_alert(self, mock_context, admin_auth):
        """Revenue milestone $10 triggers alert when crossed."""
        month = current_month_key()
        # $10 / 0.014 ≈ 714.3 stars needed for $10 milestone
        credits_sold = 715
        credits_just_sold = 10
        await MonthlyStats(
            month_key=month, total_payments=1, total_credits_sold=credits_sold
        ).insert()

        await check_and_send_alerts(mock_context.bot, credits_just_sold=credits_just_sold)

        calls = mock_context.bot.send_message.call_args_list
        texts = [c.kwargs["text"] for c in calls]
        milestone_texts = [t for t in texts if "$10" in t]
        assert len(milestone_texts) == 1, f"Expected $10 milestone alert, got: {texts}"

    async def test_revenue_milestone_not_sent_if_already_above(self, mock_context, admin_auth):
        """Milestone not sent if previous revenue was already above threshold."""
        month = current_month_key()
        # Both prev and current above $10 → no milestone crossing
        credits_sold = 800
        credits_just_sold = 5  # prev = 795 stars ≈ $11.13, current ≈ $11.20
        await MonthlyStats(
            month_key=month, total_payments=1, total_credits_sold=credits_sold
        ).insert()

        await check_and_send_alerts(mock_context.bot, credits_just_sold=credits_just_sold)

        calls = mock_context.bot.send_message.call_args_list
        texts = [c.kwargs["text"] for c in calls]
        milestone_texts = [t for t in texts if "milestone" in t.lower()]
        assert len(milestone_texts) == 0, f"Should not send milestone alert: {texts}"

    async def test_alert_not_duplicated(self, mock_context, admin_auth):
        """Same alert not sent twice in same month."""
        month = current_month_key()
        await WitUsageStats(month_key=month, language="ru", request_count=450).insert()
        await AlertState(alert_type="wit_80_ru", month_key=month).insert()

        with patch.object(settings, "wit_free_monthly_limit", 500):
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

    async def test_increment_user_stats_default_zero_audio(self):
        """Default audio_seconds=0 does not inflate stats."""
        user_id = "default_audio_user"
        await increment_user_stats(user_id)

        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_audio_seconds == 0
        assert record.total_transcriptions == 1

    async def test_increment_transcription_stats_exact_count(self):
        """Each call increments total_transcriptions by exactly 1."""
        await increment_transcription_stats()
        month_key = current_month_key()
        stats = await MonthlyStats.find_one(MonthlyStats.month_key == month_key)
        assert stats.total_transcriptions == 1

        await increment_transcription_stats()
        stats = await MonthlyStats.find_one(MonthlyStats.month_key == month_key)
        assert stats.total_transcriptions == 2  # exactly +1 each time, not +2 or +0

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
        assert record.purchased_credits == 100

        # 2. Add more credits - accumulates
        await add_credits(user_id, 50)
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_credits_purchased == 150
        assert record.purchased_credits == 150

        # 3. Spend credits - track total_tokens_used
        result = await deduct_credits(user_id, 30)
        assert result.overdraft is False
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_tokens_used == 30

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

        # 6. Purchased credits reduced by deduction (30 was from free, depends on initial state)
        total = await get_total_credits(user_id)
        assert total > 0


class TestAdminProviderPanel:
    """Test admin LLM provider panel: view, change, persistence."""

    async def test_providers_panel_shows_current_config(self):
        """Panel displays current categorization and GPT providers from settings."""

        text, markup = await _build_providers_panel()

        assert "Categ:" in text
        assert "GPT:" in text
        # Keyboard has 3 rows: categ providers, gpt providers, back button
        keyboard = markup.inline_keyboard
        assert len(keyboard) == 3
        assert keyboard[2][0].callback_data == "adm_back"

    async def test_change_categorization_provider_persists(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Changing categorization provider via admin panel persists to DB."""

        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_prov_c_groq"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        # Verify persisted in DB
        saved = await get_bot_config("categorization_provider", "")
        assert saved == const.PROVIDER_GROQ

        # Verify panel refreshed (edit_message_text called with HTML)
        mock_callback_query.edit_message_text.assert_called_once()
        call_kwargs = mock_callback_query.edit_message_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"

    async def test_change_gpt_provider_persists(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Changing GPT provider via admin panel persists to DB."""

        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_prov_g_openrouter"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        saved = await get_bot_config("gpt_provider", "")
        assert saved == const.PROVIDER_OPENROUTER

    async def test_invalid_provider_ignored(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Unknown provider name is ignored (not persisted)."""

        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_prov_c_unknown_provider"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        # Should NOT have persisted the invalid provider
        saved = await get_bot_config("categorization_provider", "")
        assert saved != "unknown_provider"

    async def test_back_button_returns_to_hub(
        self, mock_private_update, mock_context, mock_callback_query, admin_auth
    ):
        """Back button returns to admin hub."""
        mock_private_update.effective_user.id = 999
        mock_callback_query.data = "adm_back"
        mock_private_update.callback_query = mock_callback_query

        await admin_callback_router(mock_private_update, mock_context)

        mock_callback_query.edit_message_text.assert_called_once()
        call_args = mock_callback_query.edit_message_text.call_args
        # Back button should show hub keyboard (with inline buttons)
        assert "reply_markup" in call_args[1]
