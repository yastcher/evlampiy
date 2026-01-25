import pytest
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from src.dto import UserSettings

pytest_plugins = [
    "tests.fixtures",
]


@pytest.fixture(autouse=True)
async def init_db():
    """Initialize in-memory MongoDB before each test."""
    client = AsyncMongoMockClient()
    await init_beanie(database=client["test_db"], document_models=[UserSettings])
    yield
    # Cleanup after test
    await UserSettings.delete_all()
