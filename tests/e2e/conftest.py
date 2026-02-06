"""E2E test configuration — Telethon client fixtures."""

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict
from telethon import TelegramClient


class E2ESettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env")

    e2e_telegram_api_id: int = 0
    e2e_telegram_api_hash: str = ""
    e2e_telegram_phone: str = ""
    e2e_bot_username: str = ""
    e2e_session_path: str = "e2e_user"


@pytest.fixture(scope="session")
def e2e_settings():
    s = E2ESettings()
    if not s.e2e_telegram_api_id or not s.e2e_telegram_api_hash:
        pytest.skip("E2E credentials not configured (set E2E_TELEGRAM_API_ID and E2E_TELEGRAM_API_HASH)")
    if not s.e2e_bot_username:
        pytest.skip("E2E_BOT_USERNAME not configured")
    return s


@pytest.fixture(scope="session")
async def e2e_client(e2e_settings):
    client = TelegramClient(
        e2e_settings.e2e_session_path,
        e2e_settings.e2e_telegram_api_id,
        e2e_settings.e2e_telegram_api_hash,
    )
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        pytest.skip("Telethon session not authorized. Run: uv run python scripts/telethon_auth.py")
    yield client
    await client.disconnect()
