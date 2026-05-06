"""Pure-logic tests for src.services.admin_service.

Mongo-backed operations (assign_role / revoke_role / block_user / unblock_user /
change_credits) are exercised through the existing handler tests in `tests/test_admin.py`.
"""

from src.services.admin_service import parse_credits_amount, parse_user_id


class TestParseUserId:
    def test_returns_first_arg_when_numeric(self):
        assert parse_user_id(["12345"]) == "12345"

    def test_strips_whitespace(self):
        assert parse_user_id(["  9876  "]) == "9876"

    def test_rejects_non_numeric(self):
        assert parse_user_id(["abc"]) is None

    def test_rejects_mixed(self):
        assert parse_user_id(["123abc"]) is None

    def test_empty_args_returns_none(self):
        assert parse_user_id([]) is None

    def test_ignores_extra_args(self):
        assert parse_user_id(["42", "extra", "stuff"]) == "42"


class TestParseCreditsAmount:
    def test_returns_positive_int(self):
        assert parse_credits_amount("100") == 100

    def test_zero_rejected(self):
        assert parse_credits_amount("0") is None

    def test_negative_rejected(self):
        assert parse_credits_amount("-5") is None

    def test_non_numeric_rejected(self):
        assert parse_credits_amount("abc") is None

    def test_decimal_rejected(self):
        assert parse_credits_amount("1.5") is None
