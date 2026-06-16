"""Unique indexes and race-safe document creation (`get_or_create`)."""

import pymongo.errors
import pytest

from src.dto import UserCredits, UserMonthlyUsage, UserRole, UserSettings
from src.mongo import get_or_create


class TestUniqueIndexes:
    """Unique indexes reject duplicate documents at the DB level."""

    async def test_user_settings_chat_id_unique(self):
        await UserSettings(chat_id="u_1").insert()
        with pytest.raises(pymongo.errors.DuplicateKeyError):
            await UserSettings(chat_id="u_1").insert()

    async def test_user_credits_user_id_unique(self):
        await UserCredits(user_id="u_1").insert()
        with pytest.raises(pymongo.errors.DuplicateKeyError):
            await UserCredits(user_id="u_1").insert()

    async def test_user_monthly_usage_compound_unique(self):
        await UserMonthlyUsage(user_id="u_1", month_key="2026-06").insert()
        with pytest.raises(pymongo.errors.DuplicateKeyError):
            await UserMonthlyUsage(user_id="u_1", month_key="2026-06").insert()

    async def test_user_monthly_usage_distinct_month_allowed(self):
        """The compound key only collides when both fields match."""
        await UserMonthlyUsage(user_id="u_1", month_key="2026-06").insert()
        await UserMonthlyUsage(user_id="u_1", month_key="2026-07").insert()
        assert await UserMonthlyUsage.find(UserMonthlyUsage.user_id == "u_1").count() == 2

    async def test_user_role_compound_unique(self):
        await UserRole(user_id="u_1", role="vip", added_by="admin").insert()
        with pytest.raises(pymongo.errors.DuplicateKeyError):
            await UserRole(user_id="u_1", role="vip", added_by="admin2").insert()

    async def test_user_role_distinct_roles_allowed(self):
        await UserRole(user_id="u_1", role="vip", added_by="a").insert()
        await UserRole(user_id="u_1", role="tester", added_by="a").insert()
        assert await UserRole.find(UserRole.user_id == "u_1").count() == 2


class TestGetOrCreate:
    """`get_or_create` returns the existing doc, creates when absent, and survives a race."""

    async def test_returns_existing_without_creating(self):
        existing = UserSettings(chat_id="u_1")
        await existing.insert()

        result = await get_or_create(
            lambda: UserSettings.find_one(UserSettings.chat_id == "u_1"),
            lambda: UserSettings(chat_id="u_1"),
        )

        assert result.id == existing.id
        assert await UserSettings.find(UserSettings.chat_id == "u_1").count() == 1

    async def test_creates_when_absent(self):
        result = await get_or_create(
            lambda: UserSettings.find_one(UserSettings.chat_id == "u_2"),
            lambda: UserSettings(chat_id="u_2"),
        )

        assert result.chat_id == "u_2"
        assert await UserSettings.find(UserSettings.chat_id == "u_2").count() == 1

    async def test_survives_lost_insert_race(self):
        """When our insert loses the race, re-fetch the winner instead of raising."""
        winner = UserSettings(chat_id="u_3")
        await winner.insert()

        finder_calls = 0

        async def racing_finder():
            nonlocal finder_calls
            finder_calls += 1
            # First lookup mimics our read losing the race (saw nothing); the
            # post-DuplicateKeyError lookup finds the committed winner.
            if finder_calls == 1:
                return None
            return await UserSettings.find_one(UserSettings.chat_id == "u_3")

        result = await get_or_create(
            racing_finder,
            lambda: UserSettings(chat_id="u_3"),  # insert hits the unique index
        )

        assert result.id == winner.id
        assert finder_calls == 2  # re-fetched the winner after the duplicate
        assert await UserSettings.find(UserSettings.chat_id == "u_3").count() == 1

    async def test_reraises_when_winner_not_found(self):
        """A duplicate insert with no recoverable winner re-raises rather than hiding it."""
        await UserSettings(chat_id="u_4").insert()

        async def always_none():
            return None

        with pytest.raises(pymongo.errors.DuplicateKeyError):
            await get_or_create(
                always_none,
                lambda: UserSettings(chat_id="u_4"),
            )
