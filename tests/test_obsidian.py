from unittest.mock import AsyncMock, patch

from src.mongo import set_github_settings, set_save_to_obsidian
from src.obsidian import add_short_note_to_obsidian, save_transcription_to_obsidian


class TestAddShortNoteToObsidian:
    """Test GitHub note creation."""

    async def test_creates_note_successfully(self):
        """Note is created in GitHub repository."""
        chat_id = "u_obsidian_test_1"
        await set_github_settings(chat_id, "testowner", "testrepo", "ghp_testtoken")

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put:
            result = await add_short_note_to_obsidian(chat_id, "Test note content")

        assert result is True
        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args.kwargs
        assert call_kwargs["token"] == "ghp_testtoken"
        assert call_kwargs["owner"] == "testowner"
        assert call_kwargs["repo"] == "testrepo"
        assert call_kwargs["path"].startswith("income/")
        assert call_kwargs["content"] == "Test note content"

    async def test_handles_github_error(self):
        """GitHub API error returns False."""
        chat_id = "u_obsidian_test_2"
        await set_github_settings(chat_id, "testowner", "testrepo", "ghp_testtoken")

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=False)):
            result = await add_short_note_to_obsidian(chat_id, "Test note")

        assert result is False

    async def test_returns_false_when_no_text(self):
        """Returns False when no text provided."""
        result = await add_short_note_to_obsidian("u_obsidian_test_3", "")
        assert result is False

    async def test_returns_false_when_no_github_settings(self):
        """Returns False when no GitHub settings configured."""
        # No settings configured for this chat_id
        result = await add_short_note_to_obsidian("u_obsidian_no_settings", "Test note")
        assert result is False


class TestSaveTranscriptionToObsidian:
    """Test transcription saving with YAML frontmatter."""

    async def test_returns_false_when_disabled(self):
        """Returns (False, None) when save_to_obsidian is disabled."""
        chat_id = "u_transcription_disabled"
        # save_to_obsidian is False by default, no need to set anything
        success, filename = await save_transcription_to_obsidian(chat_id, "text", "telegram", "ru")

        assert success is False
        assert filename is None

    async def test_returns_false_when_no_github_settings(self):
        """Returns (False, None) when no GitHub settings configured."""
        chat_id = "u_transcription_no_github"
        await set_save_to_obsidian(chat_id, True)
        # GitHub settings not configured

        success, filename = await save_transcription_to_obsidian(chat_id, "text", "telegram", "ru")

        assert success is False
        assert filename is None

    async def test_saves_with_yaml_frontmatter(self):
        """Transcription saved with correct YAML frontmatter."""
        chat_id = "u_transcription_test_1"
        await set_save_to_obsidian(chat_id, True)
        await set_github_settings(chat_id, "user", "notes", "ghp_abc")

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put:
            success, filename = await save_transcription_to_obsidian(
                chat_id, "Hello world", "telegram", "en"
            )

        assert success is True
        assert filename is not None
        assert filename.endswith(".md")
        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args.kwargs
        assert call_kwargs["token"] == "ghp_abc"
        assert call_kwargs["owner"] == "user"
        assert call_kwargs["repo"] == "notes"
        assert call_kwargs["path"].startswith("income/")
        assert call_kwargs["path"].endswith(".md")

        content = call_kwargs["content"]
        assert content.startswith("---\n")
        assert "source: telegram" in content
        assert "language: en" in content
        assert f"chat_id: {chat_id}" in content
        assert "Hello world" in content

    async def test_saves_whatsapp_source(self):
        """Transcription from WhatsApp has correct source."""
        chat_id = "w_79001234567"
        await set_save_to_obsidian(chat_id, True)
        await set_github_settings(chat_id, "user", "notes", "ghp_abc")

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put:
            success, filename = await save_transcription_to_obsidian(
                chat_id, "Привет", "whatsapp", "ru"
            )

        assert success is True
        assert filename is not None
        content = mock_put.call_args.kwargs["content"]
        assert "source: whatsapp" in content
        assert "language: ru" in content

    async def test_group_uses_sender_settings(self):
        """In group chat, uses sender's personal settings but keeps group chat_id in frontmatter."""
        group_chat_id = "g_-1001234567890"
        sender_chat_id = "u_123"
        await set_save_to_obsidian(sender_chat_id, True)
        await set_github_settings(sender_chat_id, "sender", "vault", "ghp_sender")

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put:
            success, filename = await save_transcription_to_obsidian(
                group_chat_id, "Group note", "telegram", "en", settings_chat_id=sender_chat_id
            )

        assert success is True
        assert filename is not None
        call_kwargs = mock_put.call_args.kwargs
        assert call_kwargs["token"] == "ghp_sender"
        content = call_kwargs["content"]
        assert f"chat_id: {group_chat_id}" in content

    async def test_group_no_sender_settings_skips(self):
        """In group chat, if sender has no settings, nothing is saved."""
        group_chat_id = "g_-1001234567890"
        sender_chat_id = "u_no_settings"

        success, filename = await save_transcription_to_obsidian(
            group_chat_id, "text", "telegram", "en", settings_chat_id=sender_chat_id
        )

        assert success is False
        assert filename is None

    async def test_returns_false_on_api_failure(self):
        """Returns (False, None) when GitHub API call fails."""
        chat_id = "u_transcription_api_fail"
        await set_save_to_obsidian(chat_id, True)
        await set_github_settings(chat_id, "user", "notes", "ghp_abc")

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=False)):
            success, filename = await save_transcription_to_obsidian(
                chat_id, "text", "telegram", "ru"
            )

        assert success is False
        assert filename is None

    async def test_dual_save_includes_original_block(self):
        """When original_text differs from text, an HTML comment block is appended."""
        chat_id = "u_dual_save_test"
        await set_save_to_obsidian(chat_id, True)
        await set_github_settings(chat_id, "user", "notes", "ghp_abc")

        cleaned = "Сегодня встреча по проекту."
        original = "ну сегодня вот значит встреча по ну проекту"

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put:
            success, _filename = await save_transcription_to_obsidian(
                chat_id, cleaned, "telegram", "ru", original_text=original
            )

        assert success is True
        content = mock_put.call_args.kwargs["content"]
        assert cleaned in content
        assert "<!-- original" in content
        assert original in content
        assert "-->" in content

    async def test_no_original_block_when_texts_are_same(self):
        """No HTML comment block is added when original_text equals text."""
        chat_id = "u_same_text_test"
        await set_save_to_obsidian(chat_id, True)
        await set_github_settings(chat_id, "user", "notes", "ghp_abc")

        text = "Текст без изменений."

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put:
            await save_transcription_to_obsidian(
                chat_id, text, "telegram", "ru", original_text=text
            )

        content = mock_put.call_args.kwargs["content"]
        assert "<!-- original" not in content

    async def test_no_original_block_when_original_text_is_none(self):
        """No HTML comment block is added when original_text is None."""
        chat_id = "u_none_original_test"
        await set_save_to_obsidian(chat_id, True)
        await set_github_settings(chat_id, "user", "notes", "ghp_abc")

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put:
            await save_transcription_to_obsidian(
                chat_id, "Some text", "telegram", "ru", original_text=None
            )

        content = mock_put.call_args.kwargs["content"]
        assert "<!-- original" not in content
