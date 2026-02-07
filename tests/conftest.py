import pytest
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from src.dto import (
    AccountLink,
    AlertState,
    LinkAttempt,
    LinkCode,
    MonthlyStats,
    UsedTrial,
    UserCredits,
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
    # Cleanup after test
    for model in ALL_TEST_MODELS:
        await model.delete_all()
