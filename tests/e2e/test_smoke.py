"""E2E smoke test: send voice message to bot, verify transcription response."""

import asyncio
import logging
from pathlib import Path

import pytest
from telethon import TelegramClient

from tests.e2e.conftest import E2ESettings

logger = logging.getLogger(__name__)

VOICE_SAMPLE_PATH = Path(__file__).parent / "voice_sample.ogg"
RESPONSE_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 2
MIN_KEYWORD_MATCHES = 2
EXPECTED_KEYWORDS = ["релиз", "прошел", "успешно"]


@pytest.mark.e2e
async def test_voice_transcription_smoke(e2e_client: TelegramClient, e2e_settings: E2ESettings):
    """Send a voice message to the bot and verify transcription comes back."""
    if not VOICE_SAMPLE_PATH.exists():
        pytest.skip(f"Voice sample not found: {VOICE_SAMPLE_PATH}")

    bot_entity = await e2e_client.get_entity(e2e_settings.e2e_bot_username)

    sent = await e2e_client.send_file(
        bot_entity,
        str(VOICE_SAMPLE_PATH),
        voice_note=True,
    )
    logger.info("Sent voice message, id=%s", sent.id)

    # Poll for bot response
    response_text = None
    polls = RESPONSE_TIMEOUT_SECONDS // POLL_INTERVAL_SECONDS

    for _ in range(polls):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        messages = await e2e_client.get_messages(bot_entity, limit=5)
        for msg in messages:
            if msg.id > sent.id and msg.text and not msg.out:
                response_text = msg.text
                break
        if response_text:
            break

    assert response_text is not None, f"Bot did not respond within {RESPONSE_TIMEOUT_SECONDS}s"

    response_lower = response_text.lower()
    matched = [kw for kw in EXPECTED_KEYWORDS if kw in response_lower]
    assert len(matched) >= MIN_KEYWORD_MATCHES, (
        f"Expected at least {MIN_KEYWORD_MATCHES} of {EXPECTED_KEYWORDS} in response, "
        f"got {matched}. Full response: {response_text}"
    )
    logger.info("Smoke test passed. Response: %s", response_text)
