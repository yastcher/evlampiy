"""TROPHY-style pipeline tests for Wit.ai usage tracking and monthly rollover."""

from unittest.mock import patch

from src.config import settings
from src.wit_tracking import get_wit_usage_this_month, increment_wit_usage, is_wit_available


class TestWitUsagePipeline:
    """Pipeline integration tests: real DB, no external mocks needed."""

    async def test_usage_accumulates_across_requests(self):
        """Wit usage count accumulates correctly across multiple transcription requests."""
        # 1. Start of month: no usage recorded
        assert await get_wit_usage_this_month() == 0

        # 2. Short audio: 1 chunk → 1 Wit.ai request
        await increment_wit_usage(1)
        assert await get_wit_usage_this_month() == 1

        # 3. Long audio: 3 chunks → 3 requests, total = 4
        await increment_wit_usage(3)
        assert await get_wit_usage_this_month() == 4

        # 4. Another short audio: 1 request, total = 5
        await increment_wit_usage(1)
        assert await get_wit_usage_this_month() == 5

    async def test_monthly_rollover_resets_usage(self):
        """Usage resets to zero at the start of each new month."""
        # 1. Record usage in the current month
        await increment_wit_usage(10)
        assert await get_wit_usage_this_month() == 10

        # 2. In a future month: usage is zero (new month key, no record yet)
        with patch("src.wit_tracking.current_month_key", return_value="2099-12"):
            assert await get_wit_usage_this_month() == 0

            # 3. New month accumulates independently from current month
            await increment_wit_usage(5)
            assert await get_wit_usage_this_month() == 5

        # 4. Back to current month: original usage is preserved
        assert await get_wit_usage_this_month() == 10

    async def test_is_wit_available_reflects_db_usage(self):
        """Wit.ai availability check correctly reflects accumulated usage against the limit."""
        with patch.object(settings, "wit_free_monthly_limit", 3):
            # 1. Initially below limit: available
            assert await is_wit_available() is True

            # 2. Partially used: still available
            await increment_wit_usage(2)
            assert await is_wit_available() is True  # 2 < 3

            # 3. Reached limit: unavailable
            await increment_wit_usage(1)
            assert await is_wit_available() is False  # 3 >= 3

    async def test_increment_returns_running_total(self):
        """increment_wit_usage returns the updated running total each time."""
        # 1. First call creates a new record
        total = await increment_wit_usage(2)
        assert total == 2

        # 2. Subsequent calls add to existing record
        total = await increment_wit_usage(3)
        assert total == 5

        # 3. Single-unit increment (default)
        total = await increment_wit_usage()
        assert total == 6
