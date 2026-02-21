import pytest
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from src.dto import (
    AccountLink,
    AlertState,
    BotConfig,
    LinkAttempt,
    LinkCode,
    MonthlyStats,
    RecentTranscription,
    UsedTrial,
    UserCredits,
    UserMonthlyUsage,
    UserRole,
    UserSettings,
    WitUsageStats,
)

ALL_TEST_MODELS = [
    UserSettings,
    UserCredits,
    UsedTrial,
    WitUsageStats,
    MonthlyStats,
    AlertState,
    UserRole,
    AccountLink,
    LinkCode,
    LinkAttempt,
    UserMonthlyUsage,
    RecentTranscription,
    BotConfig,
]

pytest_plugins = [
    "tests.fixtures",
]


@pytest.fixture(autouse=True)
async def init_db():
    """Initialize in-memory MongoDB before each test."""
    client = AsyncMongoMockClient()
    await init_beanie(database=client["test_db"], document_models=ALL_TEST_MODELS)
    yield
    for model in ALL_TEST_MODELS:
        await model.delete_all()
