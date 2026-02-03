from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_private_update():
    """Mock Update object for private chat."""
    update = MagicMock()
    update.effective_chat.type = "private"
    update.effective_chat.id = 12345
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.text = ""
    update.message.message_id = 1
    update.message.voice = None
    update.callback_query = None
    return update


@pytest.fixture
def mock_group_update():
    """Mock Update object for group chat."""
    update = MagicMock()
    update.effective_chat.type = "group"
    update.effective_chat.id = -100123456
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.text = ""
    update.message.message_id = 1
    update.message.chat.id = -100123456
    update.message.voice = None
    update.callback_query = None
    return update


@pytest.fixture
def mock_context():
    """Mock Context object."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    context.bot.get_chat_member = AsyncMock()
    return context


@pytest.fixture
def mock_callback_query():
    """Mock callback query for inline button press."""
    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_telegram_voice():
    """Mock Telegram voice file with download capability."""
    voice = MagicMock()
    voice.get_file = AsyncMock()
    voice.get_file.return_value.download_as_bytearray = AsyncMock(return_value=b"fake_audio_data")
    return voice


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
    """Mock WhatsApp client."""
    wa = MagicMock()
    wa.get_media_url.return_value = "https://example.com/audio.ogg"
    wa.send_message = MagicMock()
    return wa
