import base64
from unittest.mock import AsyncMock, patch

import pytest

from src.obsidian import add_short_note_to_obsidian, save_transcription_to_obsidian

pytestmark = [pytest.mark.asyncio]


class TestAddShortNoteToObsidian:
    """Test GitHub note creation."""

    async def test_creates_note_successfully(self, mock_private_update):
        """Note is created in GitHub repository."""
        mock_private_update.message.text = "Test note content"

        github_settings = {
            "owner": "testowner",
            "repo": "testrepo",
            "token": "ghp_testtoken",
        }

        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"content": {"name": "test.md"}}

        with (
            patch("src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)),
            patch("src.obsidian.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.put.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await add_short_note_to_obsidian(mock_private_update)

        mock_client.put.assert_called_once()
        call_kwargs = mock_client.put.call_args
        assert "Bearer ghp_testtoken" in call_kwargs.kwargs["headers"]["Authorization"]

    async def test_handles_github_error(self, mock_private_update, caplog):
        """GitHub API error is logged."""
        mock_private_update.message.text = "Test note"

        github_settings = {
            "owner": "testowner",
            "repo": "testrepo",
            "token": "ghp_testtoken",
        }

        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Bad credentials"}

        with (
            patch("src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)),
            patch("src.obsidian.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.put.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await add_short_note_to_obsidian(mock_private_update)

        mock_client.put.assert_called_once()

    async def test_skips_when_no_message(self, mock_private_update):
        """Skips processing when no message."""
        mock_private_update.message = None

        await add_short_note_to_obsidian(mock_private_update)
        # No error should occur

    async def test_skips_when_no_text(self, mock_private_update):
        """Skips processing when no text in message."""
        mock_private_update.message.text = None

        await add_short_note_to_obsidian(mock_private_update)
        # No error should occur

    async def test_content_is_base64_encoded(self, mock_private_update):
        """Note content is properly base64 encoded."""
        note_text = "Hello, World!"
        mock_private_update.message.text = note_text
        expected_base64 = base64.b64encode(note_text.encode("utf-8")).decode("utf-8")

        github_settings = {
            "owner": "testowner",
            "repo": "testrepo",
            "token": "ghp_testtoken",
        }

        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"content": {"name": "test.md"}}

        with (
            patch("src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)),
            patch("src.obsidian.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.put.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await add_short_note_to_obsidian(mock_private_update)

        call_kwargs = mock_client.put.call_args
        body = call_kwargs.kwargs["json"]
        assert body["content"] == expected_base64


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
