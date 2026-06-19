from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import CallbackQuery, Chat, Message, User

import src.ai_client
import src.telegram.handlers.obsidian as obsidian_handlers
import src.whatsapp.client
from src.whatsapp.app import create_fastapi_app


def _build_user_mock(user_id: int = 12345, *, is_bot: bool = False) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.is_bot = is_bot
    user.first_name = "Test"
    user.username = "testuser"
    user.language_code = "en"
    return user


def _build_chat_mock(chat_id: int, chat_type: str) -> MagicMock:
    chat = MagicMock(spec=Chat)
    chat.id = chat_id
    chat.type = chat_type
    chat.title = None
    return chat


def _build_message_mock(*, chat_id: int, chat_type: str, user_id: int = 12345) -> MagicMock:
    """Build an aiogram-shape Message mock with answer/reply/edit_text as AsyncMocks."""
    msg = MagicMock()
    msg.__class__ = Message  # so isinstance(msg, Message) passes in handler narrowing
    msg.message_id = 1
    msg.text = ""
    msg.voice = None
    msg.audio = None
    msg.forward_origin = None
    msg.successful_payment = None
    msg.chat = _build_chat_mock(chat_id, chat_type)
    msg.from_user = _build_user_mock(user_id)
    msg.answer = AsyncMock()
    msg.reply = AsyncMock()
    msg.edit_text = AsyncMock()
    return msg


@pytest.fixture
def mock_private_update():
    """Mock aiogram Message for private chat (name kept for backwards-compat)."""
    return _build_message_mock(chat_id=12345, chat_type="private", user_id=12345)


@pytest.fixture
def mock_group_update():
    """Mock aiogram Message for group chat (name kept for backwards-compat)."""
    return _build_message_mock(chat_id=-100123456, chat_type="group", user_id=12345)


@pytest.fixture
def mock_context():
    """Mock aiogram Bot (passed as the `bot: Bot` arg in handlers)."""
    return AsyncMock()


@pytest.fixture
def mock_state():
    """Mock aiogram FSMContext."""
    state = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.get_state = AsyncMock(return_value=None)
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    return state


@pytest.fixture
def mock_callback_query():
    """Mock aiogram CallbackQuery."""
    query = MagicMock()
    query.__class__ = CallbackQuery
    query.id = "cbq_1"
    query.data = ""
    query.from_user = _build_user_mock(12345)
    query.answer = AsyncMock()
    query.message = _build_message_mock(chat_id=12345, chat_type="private", user_id=12345)
    return query


@pytest.fixture
def mock_telegram_voice():
    """Mock aiogram Voice."""
    voice = MagicMock()
    voice.file_id = "voice_file_id"
    voice.file_unique_id = "voice_unique"
    voice.duration = 5
    return voice


@pytest.fixture
def mock_telegram_audio():
    """Mock aiogram Audio."""
    audio = MagicMock()
    audio.file_id = "audio_file_id"
    audio.file_unique_id = "audio_unique"
    audio.duration = 30
    return audio


@pytest.fixture
def reset_pending_connects():
    """Clear the in-memory GitHub connect store so pending tokens don't leak between tests."""
    obsidian_handlers._pending_connects.clear()
    yield
    obsidian_handlers._pending_connects.clear()


@pytest.fixture
def mock_httpx_response_factory():
    """Factory for creating mocked httpx responses."""

    def _create(json_data=None, status_code=200):
        response = MagicMock()
        response.json.return_value = json_data or {}
        response.status_code = status_code
        return response

    return _create


@pytest.fixture
def mock_httpx_download_response():
    """Mock httpx response for file download (WhatsApp audio)."""
    response = MagicMock()
    response.content = b"fake_audio_data"
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_httpx_client_factory():
    """Factory for creating configured httpx AsyncClient mock."""

    def _create(mock_client_cls):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client
        return mock_client

    return _create


@pytest.fixture
def mock_ai_http():
    """Provide a mock httpx client for ai_client calls via get_http_client."""
    mock_client = AsyncMock()
    with patch("src.ai_client.get_http_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_rate_limiter():
    """Bypass rate limiting in tests."""
    with patch.object(src.ai_client.rate_limiter, "acquire", new_callable=AsyncMock):
        yield


@pytest.fixture
def no_fallback_keys():
    """Clear all AI provider API keys so the fallback chain doesn't interfere."""
    with (
        patch("src.ai_client.settings.gemini_api_key", ""),
        patch("src.ai_client.settings.anthropic_bot_api_key", ""),
        patch("src.ai_client.settings.gpt_token", ""),
        patch("src.ai_client.settings.groq_api_key", ""),
        patch("src.ai_client.settings.openrouter_api_key", ""),
        patch("src.ai_client.settings.deepseek_api_key", ""),
        patch("src.ai_client.settings.qwen_api_key", ""),
    ):
        yield


@pytest.fixture
def mock_ai_sleep():
    """Mock asyncio.sleep in ai_client and ai_chat (no-op, suppress actual sleeping)."""
    with (
        patch("src.ai_client.asyncio.sleep", new_callable=AsyncMock),
        patch("src.ai_chat.asyncio.sleep", new_callable=AsyncMock),
    ):
        yield


@pytest.fixture
def capture_ai_sleep():
    """Mock asyncio.sleep in ai_client and capture call durations."""
    calls: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    with patch("src.ai_client.asyncio.sleep", side_effect=_fake_sleep):
        yield calls


@pytest.fixture
def voice_external_mocks():
    """Mock external boundaries for voice handler (Trophy: real DB, mock I/O).

    transcribe_audio / save_transcription_to_obsidian / cleanup_transcript / categorize_note
    live in `src.services.voice_pipeline` after PR2 of architecture-isolation.
    send_response / check_and_send_alerts stay in the telegram adapter.
    """
    with (
        patch(
            "src.services.voice_pipeline.transcribe_audio",
            AsyncMock(return_value=("Hello world", 5, 1)),
        ) as mock_transcribe,
        patch("src.telegram.handlers.voice.send_response", AsyncMock()) as mock_send,
        patch(
            "src.services.voice_pipeline.save_transcription_to_obsidian",
            AsyncMock(return_value=(False, None)),
        ) as mock_obsidian,
        patch("src.telegram.handlers.voice.check_and_send_alerts", AsyncMock()) as mock_alerts,
        patch(
            "src.services.voice_pipeline.cleanup_transcript",
            AsyncMock(side_effect=lambda t, **kwargs: t),
        ) as mock_cleanup,
        patch(
            "src.services.voice_pipeline.categorize_note",
            AsyncMock(return_value="work"),
        ) as mock_categorize,
    ):
        yield {
            "transcribe": mock_transcribe,
            "send": mock_send,
            "obsidian": mock_obsidian,
            "alerts": mock_alerts,
            "cleanup": mock_cleanup,
            "categorize": mock_categorize,
        }


@pytest.fixture
def mock_whatsapp_message():
    """Mock WhatsApp incoming message."""
    message = MagicMock()
    message.from_user.wa_id = "1234567890"
    message.voice = MagicMock()
    message.voice.id = "media_123"
    message.audio = None
    return message


@pytest.fixture
def mock_whatsapp_client():
    """Mock WhatsApp client (pywa_async — methods are awaitables)."""
    wa = MagicMock()
    wa.get_media_url = AsyncMock(return_value="https://example.com/audio.ogg")
    wa.send_message = AsyncMock()
    return wa


@pytest.fixture
def whatsapp_voice_external_mocks(mock_httpx_download_response):
    """Mock external boundaries for WhatsApp voice handler (Trophy: real DB, mock I/O)."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_httpx_download_response)

    with (
        patch("src.whatsapp.handlers.httpx.AsyncClient") as mock_client_class,
        patch(
            "src.services.voice_pipeline.transcribe_audio",
            AsyncMock(return_value=("Hello world", 5, 1)),
        ) as mock_transcribe,
        patch(
            "src.services.voice_pipeline.save_transcription_to_obsidian",
            AsyncMock(return_value=(True, "note.md")),
        ) as mock_save,
        patch("src.services.voice_pipeline.categorize_note", AsyncMock()) as mock_categorize,
        patch(
            "src.services.voice_pipeline.cleanup_transcript",
            AsyncMock(side_effect=lambda t, **kwargs: t),
        ) as mock_cleanup,
    ):
        mock_client_class.return_value.__aenter__.return_value = mock_client
        yield {
            "http_client": mock_client,
            "transcribe": mock_transcribe,
            "save": mock_save,
            "categorize": mock_categorize,
            "cleanup": mock_cleanup,
        }


@pytest.fixture
def make_update_factory():
    """Factory for creating aiogram event mocks with configurable is_bot flag.

    Returned object is shaped like a Message (has `from_user`) — used by tests
    that exercise the bot-sender outer middleware.
    """

    def _create(*, is_bot: bool | None) -> MagicMock:
        event = MagicMock()
        if is_bot is None:
            event.from_user = None
        else:
            event.from_user = _build_user_mock(999, is_bot=is_bot)
        return event

    return _create


@pytest.fixture
def mock_selftest_cleanup():
    """Factory for mocking selftest cleanup_text with configurable return value."""

    def _create(return_value="cleaned text"):
        return patch("src.selftest.cleanup_text", new_callable=AsyncMock, return_value=return_value)

    return _create


@pytest.fixture
def mock_bot():
    """Mock aiogram Bot for selftest."""
    bot = AsyncMock()
    bot.send_voice = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def _patch_settings(tmp_path):
    """Patch selftest settings with a temp audio file."""
    sample_file = tmp_path / "test_sample.ogg"
    sample_file.write_bytes(b"fake_ogg_audio_data")
    with (
        patch("src.selftest.settings") as mock_settings,
        patch("src.selftest.get_audio_duration_seconds", return_value=5),
    ):
        mock_settings.admin_user_ids = {"12345"}
        mock_settings.selftest_sample_path = str(sample_file)
        mock_settings.default_language = "ru"
        mock_settings.groq_api_key = ""
        mock_settings.gpt_provider = "deepseek"
        mock_settings.categorization_provider = "deepseek"
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.wit_ru_token = "test-token"
        yield mock_settings


@pytest.fixture
def admin_auth():
    """Patch settings to treat user 999 as admin for the test duration."""
    with patch("src.config.settings.admin_user_ids_raw", "999"):
        yield


@pytest.fixture
def fastapi_app_no_whatsapp():
    """Real FastAPI app with WhatsApp disabled — does not depend on local .env.

    Patches `settings` seen by `src.whatsapp.client` to have empty credentials so
    `init_whatsapp_client()` returns None and WhatsApp wiring is skipped.
    """
    with patch("src.whatsapp.client.settings") as mock_settings:
        mock_settings.whatsapp_token = ""
        mock_settings.whatsapp_phone_id = ""
        src.whatsapp.client._WhatsAppClientHolder.instance = None
        yield create_fastapi_app()


@pytest.fixture
def mock_audio_segment_factory():
    """Factory for creating AudioSegment mocks with configurable duration."""

    def _create(length_ms: int = 5000) -> MagicMock:
        seg = MagicMock()
        seg.__len__ = MagicMock(return_value=length_ms)
        seg.__getitem__ = MagicMock(return_value=seg)
        seg.export = MagicMock()
        return seg

    return _create
