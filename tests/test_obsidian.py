from unittest.mock import AsyncMock, patch

import pytest

from src.obsidian import add_short_note_to_obsidian, save_transcription_to_obsidian

pytestmark = [pytest.mark.asyncio]


class TestAddShortNoteToObsidian:
    """Test GitHub note creation."""

    async def test_creates_note_successfully(self):
        """Note is created in GitHub repository."""
        github_settings = {
            "owner": "testowner",
            "repo": "testrepo",
            "token": "ghp_testtoken",
        }

        with (
            patch("src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)),
            patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put,
        ):
            result = await add_short_note_to_obsidian("u_12345", "Test note content")

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
        github_settings = {
            "owner": "testowner",
            "repo": "testrepo",
            "token": "ghp_testtoken",
        }

        with (
            patch("src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)),
            patch("src.obsidian.put_github_file", AsyncMock(return_value=False)),
        ):
            result = await add_short_note_to_obsidian("u_12345", "Test note")

        assert result is False

    async def test_returns_false_when_no_text(self):
        """Returns False when no text provided."""
        result = await add_short_note_to_obsidian("u_12345", "")
        assert result is False

    async def test_returns_false_when_no_github_settings(self):
        """Returns False when no GitHub settings configured."""
        with patch("src.obsidian.get_github_settings", AsyncMock(return_value=None)):
            result = await add_short_note_to_obsidian("u_12345", "Test note")

        assert result is False


class TestSaveTranscriptionToObsidian:
    """Test transcription saving with YAML frontmatter."""

    async def test_returns_false_when_disabled(self):
        """Returns (False, None) when save_to_obsidian is disabled."""
        with patch("src.obsidian.get_save_to_obsidian", AsyncMock(return_value=False)):
            success, filename = await save_transcription_to_obsidian("u_12345", "text", "telegram", "ru")

        assert success is False
        assert filename is None

    async def test_returns_false_when_no_github_settings(self):
        """Returns (False, None) when no GitHub settings configured."""
        with (
            patch("src.obsidian.get_save_to_obsidian", AsyncMock(return_value=True)),
            patch("src.obsidian.get_github_settings", AsyncMock(return_value={})),
        ):
            success, filename = await save_transcription_to_obsidian("u_12345", "text", "telegram", "ru")

        assert success is False
        assert filename is None

    async def test_saves_with_yaml_frontmatter(self):
        """Transcription saved with correct YAML frontmatter."""
        github_settings = {"owner": "user", "repo": "notes", "token": "ghp_abc"}

        with (
            patch("src.obsidian.get_save_to_obsidian", AsyncMock(return_value=True)),
            patch("src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)),
            patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put,
        ):
            success, filename = await save_transcription_to_obsidian(
                "u_12345", "Hello world", "telegram", "en"
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
        assert "chat_id: u_12345" in content
        assert "Hello world" in content

    async def test_saves_whatsapp_source(self):
        """Transcription from WhatsApp has correct source."""
        github_settings = {"owner": "user", "repo": "notes", "token": "ghp_abc"}

        with (
            patch("src.obsidian.get_save_to_obsidian", AsyncMock(return_value=True)),
            patch("src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)),
            patch("src.obsidian.put_github_file", AsyncMock(return_value=True)) as mock_put,
        ):
            success, filename = await save_transcription_to_obsidian(
                "w_79001234567", "Привет", "whatsapp", "ru"
            )

        assert success is True
        assert filename is not None
        content = mock_put.call_args.kwargs["content"]
        assert "source: whatsapp" in content
        assert "language: ru" in content

    async def test_returns_false_on_api_failure(self):
        """Returns (False, None) when GitHub API call fails."""
        github_settings = {"owner": "user", "repo": "notes", "token": "ghp_abc"}

        with (
            patch("src.obsidian.get_save_to_obsidian", AsyncMock(return_value=True)),
            patch("src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)),
            patch("src.obsidian.put_github_file", AsyncMock(return_value=False)),
        ):
            success, filename = await save_transcription_to_obsidian("u_12345", "text", "telegram", "ru")

        assert success is False
        assert filename is None
