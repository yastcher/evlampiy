"""Tests for monetization: credits, tokens, billing, blocked, wit tracking."""

from unittest.mock import patch

from src.credits import (
    DeductResult,
    add_credits,
    admin_add_credits,
    calculate_token_cost,
    can_perform_operation,
    current_month_key,
    deduct_credits,
    get_credits,
    get_total_credits,
    get_user_tier,
    hash_user_id,
    is_blocked_user,
    is_vip_user,
    record_user_usage,
)
from src.dto import UserCredits, UserMonthlyUsage, UserTier
from src.mongo import add_user_role, remove_user_role
from src.wit_tracking import get_wit_usage_this_month, increment_wit_usage, is_wit_available


class TestTokenCost:
    """Test token cost calculation."""

    def test_short_audio_minimum_one_token(self):
        assert calculate_token_cost(1) == 1
        assert calculate_token_cost(5) == 1
        assert calculate_token_cost(19) == 1

    def test_exact_boundary(self):
        assert calculate_token_cost(20) == 1
        assert calculate_token_cost(21) == 2
        assert calculate_token_cost(40) == 2

    def test_longer_audio(self):
        assert calculate_token_cost(60) == 3
        assert calculate_token_cost(600) == 30

    def test_zero_duration(self):
        assert calculate_token_cost(0) == 1  # min 1


class TestCreditFlow:
    async def test_new_user_has_free_credits(self):
        """New user starts with free monthly tokens."""
        user_id = "new_user"
        free, purchased = await get_credits(user_id)
        assert free == 10
        assert purchased == 0
        assert await get_total_credits(user_id) == 10

    async def test_add_purchased_credits(self):
        """Adding credits goes to purchased_credits."""
        user_id = "credit_flow_user"
        new_purchased = await add_credits(user_id, 15)
        assert new_purchased == 15

        free, purchased = await get_credits(user_id)
        assert free == 10
        assert purchased == 15
        assert await get_total_credits(user_id) == 25

    async def test_add_credits_sets_paid_tier(self):
        """Adding credits changes tier to PAID."""
        user_id = "tier_user"
        assert await get_user_tier(user_id) == UserTier.FREE
        await add_credits(user_id, 5)
        assert await get_user_tier(user_id) == UserTier.PAID

    async def test_admin_add_credits_keeps_tier(self):
        """Admin-added credits do not change tier."""
        user_id = "admin_credit_user"
        assert await get_user_tier(user_id) == UserTier.FREE
        balance = await admin_add_credits(user_id, 10)
        assert balance == 10
        assert await get_user_tier(user_id) == UserTier.FREE

    async def test_can_perform_with_free_credits(self):
        """New user can perform operations with free credits."""
        user_id = "can_perform_user"
        ok, msg = await can_perform_operation(user_id, 5)
        assert ok is True
        assert msg == ""

    async def test_cannot_perform_when_exhausted(self):
        """Cannot perform when total credits are insufficient."""
        user_id = "exhausted_user"
        ok, msg = await can_perform_operation(user_id, 100)
        assert ok is False
        assert msg == "insufficient_credits"

    @patch("src.credits.settings")
    async def test_vip_always_can_perform(self, mock_settings):
        """VIP users can always perform operations."""
        vip_id = "42"
        mock_settings.vip_user_ids = {vip_id}
        mock_settings.admin_user_ids = set()

        assert await is_vip_user(vip_id) is True
        assert await get_user_tier(vip_id) == UserTier.VIP
        ok, _ = await can_perform_operation(vip_id, 10000)
        assert ok is True

    def test_user_hash_uniqueness(self):
        """Each user_id produces a unique hash."""
        hash1 = hash_user_id("111")
        hash2 = hash_user_id("222")
        hash3 = hash_user_id("111")
        assert hash1 != hash2
        assert hash1 == hash3


class TestDeductCredits:
    """Test deduction: free first, then purchased, soft overdraft."""

    async def test_deduct_from_free_first(self):
        """Deduction takes from free credits first."""
        user_id = "deduct_free_first"
        await add_credits(user_id, 5)

        result = await deduct_credits(user_id, 3)
        assert isinstance(result, DeductResult)
        assert result.free_used == 3
        assert result.purchased_used == 0
        assert result.overdraft is False

        free, purchased = await get_credits(user_id)
        assert free == 7
        assert purchased == 5

    async def test_deduct_spills_to_purchased(self):
        """When free credits exhausted, deduction spills to purchased."""
        user_id = "deduct_spill"
        await add_credits(user_id, 5)

        # Deduct 12: 10 free + 2 purchased
        result = await deduct_credits(user_id, 12)
        assert result.free_used == 10
        assert result.purchased_used == 2
        assert result.overdraft is False

        free, purchased = await get_credits(user_id)
        assert free == 0
        assert purchased == 3

    async def test_soft_overdraft(self):
        """Overdraft: deducts what's available, never below 0."""
        user_id = "overdraft_user"
        # Only has 10 free tokens, no purchased
        result = await deduct_credits(user_id, 50)
        assert result.free_used == 10
        assert result.purchased_used == 0
        assert result.overdraft is True

        free, purchased = await get_credits(user_id)
        assert free == 0
        assert purchased == 0

    async def test_deduct_zero_available(self):
        """Deducting from user with 0 balance returns overdraft with 0 used."""
        user_id = "zero_user"
        # First exhaust free credits
        await deduct_credits(user_id, 100)

        result = await deduct_credits(user_id, 5)
        assert result.free_used == 0
        assert result.purchased_used == 0
        assert result.overdraft is True

    async def test_deduct_tracks_tokens_used(self):
        """Deduction increments total_tokens_used."""
        user_id = "track_user"
        await deduct_credits(user_id, 3)

        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        assert record.total_tokens_used == 3


class TestLazyReset:
    """Test lazy monthly reset of free credits."""

    async def test_fresh_month_resets_free_credits(self):
        """Free credits are reset when month changes."""
        user_id = "reset_user"

        # Exhaust free credits
        await deduct_credits(user_id, 10)
        free, _ = await get_credits(user_id)
        assert free == 0

        # Simulate month change
        with patch("src.credits.current_month_key", return_value="2099-01"):
            free, _ = await get_credits(user_id)
            assert free == 10

    async def test_same_month_no_reset(self):
        """Free credits are NOT reset within the same month."""
        user_id = "no_reset_user"
        await deduct_credits(user_id, 5)

        free, _ = await get_credits(user_id)
        assert free == 5  # not reset


class TestBlockedUser:
    """Test blocked user functionality."""

    async def test_block_and_check(self):
        user_id = "blocked_user"
        assert await is_blocked_user(user_id) is False
        await add_user_role(user_id, "blocked", "admin")
        assert await is_blocked_user(user_id) is True

    async def test_unblock(self):
        user_id = "unblock_user"
        await add_user_role(user_id, "blocked", "admin")
        assert await is_blocked_user(user_id) is True
        await remove_user_role(user_id, "blocked")
        assert await is_blocked_user(user_id) is False


class TestRecordUserUsage:
    """Test monthly usage tracking."""

    async def test_records_usage(self):
        user_id = "usage_user"
        await record_user_usage(user_id, audio_seconds=30, tokens=2, free_used=2, purchased_used=0)

        month = current_month_key()
        record = await UserMonthlyUsage.find_one(
            UserMonthlyUsage.user_id == user_id,
            UserMonthlyUsage.month_key == month,
        )
        assert record is not None
        assert record.transcriptions == 1
        assert record.audio_seconds == 30
        assert record.tokens_used == 2
        assert record.free_tokens_used == 2
        assert record.purchased_tokens_used == 0

    async def test_accumulates_usage(self):
        user_id = "accumulate_user"
        await record_user_usage(user_id, audio_seconds=10, tokens=1, free_used=1, purchased_used=0)
        await record_user_usage(user_id, audio_seconds=20, tokens=1, free_used=0, purchased_used=1)

        month = current_month_key()
        record = await UserMonthlyUsage.find_one(
            UserMonthlyUsage.user_id == user_id,
            UserMonthlyUsage.month_key == month,
        )
        assert record.transcriptions == 2
        assert record.audio_seconds == 30
        assert record.tokens_used == 2
        assert record.free_tokens_used == 1
        assert record.purchased_tokens_used == 1


class TestWitUsageLimits:
    @patch("src.wit_tracking.settings")
    async def test_complete_wit_usage_flow(self, mock_settings):
        """Test complete Wit.ai usage tracking flow."""
        mock_settings.wit_free_monthly_limit = 3

        assert await get_wit_usage_this_month("ru") == 0
        assert await is_wit_available("ru") is True

        count = await increment_wit_usage(language="ru")
        assert count == 1
        assert await get_wit_usage_this_month("ru") == 1

        await increment_wit_usage(language="ru")
        count = await increment_wit_usage(language="ru")
        assert count == 3

        assert await is_wit_available("ru") is False

        await increment_wit_usage(language="ru")
        assert await is_wit_available("ru") is False
