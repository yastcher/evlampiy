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

    async def test_returns_false_on_api_failure(self):
        """Returns (False, None) when GitHub API call fails."""
        chat_id = "u_transcription_api_fail"
        await set_save_to_obsidian(chat_id, True)
        await set_github_settings(chat_id, "user", "notes", "ghp_abc")

        with patch("src.obsidian.put_github_file", AsyncMock(return_value=False)):
            success, filename = await save_transcription_to_obsidian(chat_id, "text", "telegram", "ru")

        assert success is False
        assert filename is None
