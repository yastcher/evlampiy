from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_empty_settings():
    """Mock settings with empty VIP/admin lists."""
    with (
        patch("src.credits.settings.vip_user_ids_raw", ""),
        patch("src.credits.settings.admin_user_ids_raw", ""),
    ):
        yield


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
