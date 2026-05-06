"""Tests for src.services.payments_service.

Adapter-level flow (keyboard, send_invoice, alerts wiring) lives in tests/test_payments.py
under TestPaymentFlow / TestBuyCommand / TestBuyPackageCallback / TestPreCheckout /
TestBalanceCommand.
"""

from src.credits import get_total_credits
from src.services.payments_service import (
    CREDIT_PACKAGES,
    AwardResult,
    award_tokens,
    package_payload,
    tokens_for_payload,
)


class TestPackagePayload:
    def test_format(self):
        assert package_payload(0) == "buy_tokens_0"
        assert package_payload(3) == "buy_tokens_3"


class TestTokensForPayload:
    def test_package_payload_uses_package_tokens(self):
        # Medium = index 1 = 30 tokens, regardless of total_amount (Stars paid)
        assert tokens_for_payload("buy_tokens_1", total_amount=25) == CREDIT_PACKAGES[1]["tokens"]
        assert tokens_for_payload("buy_tokens_1", total_amount=999) == 30

    def test_each_package_index(self):
        for idx, pkg in enumerate(CREDIT_PACKAGES):
            assert tokens_for_payload(f"buy_tokens_{idx}", total_amount=0) == pkg["tokens"]

    def test_legacy_payload_falls_back_to_total_amount(self):
        # Unknown payload (e.g. manual top-up) → award the raw stars amount
        assert tokens_for_payload("buy_credits", total_amount=10) == 10
        assert tokens_for_payload("", total_amount=42) == 42


class TestAwardTokens:
    async def test_package_payment_credits_package_tokens(self):
        user_id = "pay_1"
        before = await get_total_credits(user_id)

        result = await award_tokens(user_id, "buy_tokens_2", total_amount=50)

        assert isinstance(result, AwardResult)
        # Large package = 65 tokens
        assert result.tokens_added == 65
        assert result.new_total_balance == before + 65
        assert await get_total_credits(user_id) == before + 65

    async def test_legacy_payment_credits_total_amount(self):
        user_id = "pay_2"
        before = await get_total_credits(user_id)

        result = await award_tokens(user_id, "buy_credits", total_amount=10)

        assert result.tokens_added == 10
        assert result.new_total_balance == before + 10

    async def test_returned_total_reflects_new_balance(self):
        user_id = "pay_3"
        # First purchase
        first = await award_tokens(user_id, "buy_tokens_0", total_amount=10)
        # Second purchase — balance accumulates
        second = await award_tokens(user_id, "buy_tokens_0", total_amount=10)
        assert second.new_total_balance == first.new_total_balance + 10
