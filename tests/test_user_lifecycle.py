"""Integration test for complete user lifecycle."""

from src.config import settings
from src.credits import (
    add_credits,
    can_perform_operation,
    deduct_credits,
    get_credits,
    get_user_tier,
    grant_initial_credits_if_eligible,
)
from src.dto import UserCredits, UserTier


class TestUserLifecycle:
    """Full user lifecycle integration test."""

    async def test_complete_user_flow(self):
        """Test complete user journey from registration to deletion."""
        user_id = "999999"
        other_user_id = "888888"

        # 1. New user has zero balance and FREE tier
        assert await get_credits(user_id) == 0
        assert await get_user_tier(user_id) == UserTier.FREE

        # 2. Grant initial credits succeeds first time
        result = await grant_initial_credits_if_eligible(user_id)
        assert result is True
        assert await get_credits(user_id) == settings.initial_credits

        # 3. Grant initial credits fails second time (abuse protection)
        result = await grant_initial_credits_if_eligible(user_id)
        assert result is False
        assert await get_credits(user_id) == settings.initial_credits

        # 4. Add credits changes tier to PAID
        await add_credits(user_id, 10)
        assert await get_user_tier(user_id) == UserTier.PAID
        assert await get_credits(user_id) == settings.initial_credits + 10

        # 5. Can perform operation with sufficient credits
        ok, msg = await can_perform_operation(user_id, 1)
        assert ok is True
        assert msg == ""

        # 6. Deduct credits succeeds
        result = await deduct_credits(user_id, 5)
        assert result is True
        assert await get_credits(user_id) == settings.initial_credits + 10 - 5

        # 7. Deduct more than available fails
        current_balance = await get_credits(user_id)
        result = await deduct_credits(user_id, current_balance + 100)
        assert result is False
        assert await get_credits(user_id) == current_balance

        # 8. Delete user data (simulate account deletion)
        record = await UserCredits.find_one(UserCredits.user_id == user_id)
        await record.delete()

        # 9. Same user_id cannot get initial credits again (hash preserved in UsedTrial)
        result = await grant_initial_credits_if_eligible(user_id)
        assert result is False
        assert await get_credits(user_id) == 0

        # 10. Different user_id can get initial credits normally
        result = await grant_initial_credits_if_eligible(other_user_id)
        assert result is True
        assert await get_credits(other_user_id) == settings.initial_credits
