"""Tests for monetization: credits, VIP, trial, wit tracking."""

from unittest.mock import patch

from src.credits import (
    add_credits,
    can_perform_operation,
    deduct_credits,
    get_credits,
    get_user_tier,
    grant_initial_credits_if_eligible,
    hash_user_id,
    is_vip_user,
)
from src.dto import UserTier
from src.wit_tracking import get_wit_usage_this_month, increment_wit_usage, is_wit_available


class TestCreditFlow:
    async def test_new_user_has_zero_credits(self):
        assert await get_credits(111) == 0

    async def test_add_credits(self):
        new_balance = await add_credits(111, 5)
        assert new_balance == 5
        assert await get_credits(111) == 5

    async def test_add_credits_sets_paid_tier(self):
        await add_credits(111, 5)
        tier = await get_user_tier(111)
        assert tier == UserTier.PAID

    async def test_deduct_credits_success(self):
        await add_credits(111, 5)
        result = await deduct_credits(111, 2)
        assert result is True
        assert await get_credits(111) == 3

    async def test_deduct_credits_insufficient(self):
        await add_credits(111, 1)
        result = await deduct_credits(111, 2)
        assert result is False
        assert await get_credits(111) == 1

    async def test_deduct_credits_zero_balance(self):
        result = await deduct_credits(111, 1)
        assert result is False

    @patch("src.credits.settings")
    async def test_vip_user(self, mock_settings):
        mock_settings.vip_user_ids = {42}
        assert is_vip_user(42) is True
        assert is_vip_user(99) is False

    @patch("src.credits.settings")
    async def test_vip_tier(self, mock_settings):
        mock_settings.vip_user_ids = {42}
        tier = await get_user_tier(42)
        assert tier == UserTier.VIP

    async def test_free_tier_default(self):
        tier = await get_user_tier(111)
        assert tier == UserTier.FREE

    @patch("src.credits.settings")
    async def test_grant_initial_credits_new_user(self, mock_settings):
        mock_settings.initial_credits = 3
        mock_settings.vip_user_ids = set()
        result = await grant_initial_credits_if_eligible(111)
        assert result is True
        assert await get_credits(111) == 3

    @patch("src.credits.settings")
    async def test_grant_initial_credits_already_used(self, mock_settings):
        mock_settings.initial_credits = 3
        mock_settings.vip_user_ids = set()
        await grant_initial_credits_if_eligible(111)
        result = await grant_initial_credits_if_eligible(111)
        assert result is False
        assert await get_credits(111) == 3

    @patch("src.credits.settings")
    async def test_trial_abuse_different_accounts_same_hash_impossible(self, mock_settings):
        """Each user_id produces a unique hash."""
        mock_settings.initial_credits = 3
        mock_settings.vip_user_ids = set()
        hash1 = hash_user_id(111)
        hash2 = hash_user_id(222)
        assert hash1 != hash2

    @patch("src.credits.settings")
    async def test_can_perform_vip_always(self, mock_settings):
        mock_settings.vip_user_ids = {42}
        mock_settings.credit_cost_voice = 1
        ok, msg = await can_perform_operation(42, 1)
        assert ok is True

    @patch("src.credits.settings")
    async def test_can_perform_insufficient(self, mock_settings):
        mock_settings.vip_user_ids = set()
        ok, msg = await can_perform_operation(111, 1)
        assert ok is False
        assert msg != ""

    async def test_can_perform_with_credits(self):
        await add_credits(111, 5)
        ok, msg = await can_perform_operation(111, 1)
        assert ok is True


class TestWitUsageLimits:
    @patch("src.wit_tracking.settings")
    async def test_complete_wit_usage_flow(self, mock_settings):
        """Test complete Wit.ai usage tracking flow."""
        mock_settings.wit_free_monthly_limit = 3

        # 1. Initial usage is zero
        assert await get_wit_usage_this_month() == 0

        # 2. Available when under limit
        assert await is_wit_available() is True

        # 3. First increment
        count = await increment_wit_usage()
        assert count == 1
        assert await get_wit_usage_this_month() == 1

        # 4. Multiple increments
        await increment_wit_usage()
        count = await increment_wit_usage()
        assert count == 3

        # 5. Unavailable when at limit
        assert await is_wit_available() is False

        # 6. Still unavailable after exceeding
        await increment_wit_usage()
        assert await is_wit_available() is False
