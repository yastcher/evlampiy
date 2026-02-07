"""Tests for monetization: credits, VIP, trial, wit tracking."""

from unittest.mock import patch

from src.credits import (
    add_credits,
    can_perform_operation,
    deduct_credits,
    get_credits,
    get_user_tier,
    hash_user_id,
    is_vip_user,
)
from src.dto import UserTier
from src.wit_tracking import get_wit_usage_this_month, increment_wit_usage, is_wit_available


class TestCreditFlow:
    async def test_complete_credit_operations_flow(self):
        """Test complete credit operations: add, deduct, check balance."""
        user_id = "credit_flow_user"

        # 1. New user starts with zero credits and FREE tier
        assert await get_credits(user_id) == 0
        assert await get_user_tier(user_id) == UserTier.FREE

        # 2. Add credits — balance increases, tier becomes PAID
        new_balance = await add_credits(user_id, 10)
        assert new_balance == 10
        assert await get_credits(user_id) == 10
        assert await get_user_tier(user_id) == UserTier.PAID

        # 3. Can perform operation with sufficient credits
        ok, msg = await can_perform_operation(user_id, 5)
        assert ok is True
        assert msg == ""

        # 4. Deduct credits succeeds
        result = await deduct_credits(user_id, 3)
        assert result is True
        assert await get_credits(user_id) == 7

        # 5. Deduct more than available fails, balance unchanged
        result = await deduct_credits(user_id, 100)
        assert result is False
        assert await get_credits(user_id) == 7

        # 6. Deduct remaining credits
        await deduct_credits(user_id, 7)
        assert await get_credits(user_id) == 0

        # 7. Cannot perform operation without credits
        ok, msg = await can_perform_operation(user_id, 1)
        assert ok is False
        assert msg == "insufficient_credits"

        # 8. Deduct from zero balance fails
        result = await deduct_credits(user_id, 1)
        assert result is False

    @patch("src.credits.settings")
    async def test_vip_user_flow(self, mock_settings):
        """Test VIP user privileges: unlimited access, VIP tier."""
        vip_id = "42"
        regular_id = "99"

        mock_settings.vip_user_ids = {vip_id}
        mock_settings.admin_user_ids = set()

        # 1. VIP check
        assert await is_vip_user(vip_id) is True
        assert await is_vip_user(regular_id) is False

        # 2. VIP has VIP tier (even without credits)
        assert await get_user_tier(vip_id) == UserTier.VIP

        # 3. VIP can always perform operations (no credits needed)
        ok, _msg = await can_perform_operation(vip_id, 1000)
        assert ok is True

        # 4. Regular user without credits cannot perform
        ok, _msg = await can_perform_operation(regular_id, 1)
        assert ok is False

    def test_user_hash_uniqueness(self):
        """Each user_id produces a unique hash."""
        hash1 = hash_user_id("111")
        hash2 = hash_user_id("222")
        hash3 = hash_user_id("111")

        assert hash1 != hash2
        assert hash1 == hash3


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
