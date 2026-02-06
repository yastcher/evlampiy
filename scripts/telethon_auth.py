"""One-time interactive script to authorize Telethon session.

Usage:
    uv run python scripts/telethon_auth.py

Produces a .session file used by e2e tests.
Deploy this file to the server alongside the code.
"""

import asyncio
import os

from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()


async def main():
    api_id = int(os.environ["E2E_TELEGRAM_API_ID"])
    api_hash = os.environ["E2E_TELEGRAM_API_HASH"]
    phone = os.environ["E2E_TELEGRAM_PHONE"]
    session_path = os.environ.get("E2E_SESSION_PATH", "e2e_user")

    client = TelegramClient(session_path, api_id, api_hash)
    await client.start(phone=phone)
    print(f"Session saved to {session_path}.session")
    await client.disconnect()


asyncio.run(main())
