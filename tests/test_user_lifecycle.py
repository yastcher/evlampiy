"""Integration test for complete user lifecycle with new billing model."""

from unittest.mock import patch

from src.credits import (
    add_credits,
    can_perform_operation,
    deduct_credits,
    get_credits,
    get_total_credits,
    get_user_tier,
)
from src.dto import UserCredits, UserTier


class TestUserLifecycle:
    """Full user lifecycle integration test with token-based billing."""

    async def test_complete_user_flow(self):
        """Test complete user journey: free tokens → purchase → deduction → month reset."""
        user_id = "999999"

        # 1. New user has 10 free tokens and FREE tier
        free, purchased = await get_credits(user_id)
        assert free == 10
        assert purchased == 0
        assert await get_total_credits(user_id) == 10
        assert await get_user_tier(user_id) == UserTier.FREE

        # 2. Can perform operations with free tokens
        ok, msg = await can_perform_operation(user_id, 5)
        assert ok is True
        assert msg == ""

        # 3. Deduct uses free tokens first
        result = await deduct_credits(user_id, 3)
        assert result.free_used == 3
        assert result.purchased_used == 0
        assert result.overdraft is False

        free, purchased = await get_credits(user_id)
        assert free == 7
        assert purchased == 0

        # 4. Purchase changes tier to PAID
        await add_credits(user_id, 20)
        assert await get_user_tier(user_id) == UserTier.PAID
        assert await get_total_credits(user_id) == 27  # 7 free + 20 purchased

        # 5. Deduct spills from free to purchased
        result = await deduct_credits(user_id, 10)
        assert result.free_used == 7
        assert result.purchased_used == 3
        assert result.overdraft is False

        free, purchased = await get_credits(user_id)
        assert free == 0
        assert purchased == 17

        # 6. Overdraft: deducts what's available
        result = await deduct_credits(user_id, 100)
        assert result.free_used == 0
        assert result.purchased_used == 17
        assert result.overdraft is True

        assert await get_total_credits(user_id) == 0

        # 7. Cannot perform when empty
        ok, msg = await can_perform_operation(user_id, 1)
        assert ok is False
        assert msg == "insufficient_credits"

        # 8. Month rollover resets free tokens
        with patch("src.credits.current_month_key", return_value="2099-12"):
            free, purchased = await get_credits(user_id)
            assert free == 10  # reset
            assert purchased == 0  # still 0

            # Can perform again with fresh free tokens
            ok, _ = await can_perform_operation(user_id, 5)
            assert ok is True

    async def test_delete_and_rejoin(self):
        """After account deletion, user gets fresh free tokens (no UsedTrial needed)."""
        user_id = "888888"

        # Use some tokens
        await deduct_credits(user_id, 5)
        assert await get_total_credits(user_id) == 5

        # Delete user record
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        await record.delete()

        # New session: user gets fresh free tokens
        free, purchased = await get_credits(user_id)
        assert free == 10
        assert purchased == 0
