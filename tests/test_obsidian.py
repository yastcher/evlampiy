import base64
import re
from unittest.mock import AsyncMock, patch

import pytest
import responses

from src.obsidian import add_short_note_to_obsidian

pytestmark = [pytest.mark.asyncio]


class TestAddShortNoteToObsidian:
    """Test GitHub note creation."""

    @responses.activate
    async def test_creates_note_successfully(self, mock_private_update):
        """Note is created in GitHub repository."""
        mock_private_update.message.text = "Test note content"

        github_settings = {
            "owner": "testowner",
            "repo": "testrepo",
            "token": "ghp_testtoken",
        }

        responses.add(
            responses.PUT,
            re.compile(
                r"https://api\.github\.com/repos/testowner/testrepo/contents/income/.+"
            ),
            json={"content": {"name": "test.md"}},
            status=201,
        )

        with patch(
            "src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)
        ):
            await add_short_note_to_obsidian(mock_private_update)

        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert "Bearer ghp_testtoken" in request.headers["Authorization"]

    @responses.activate
    async def test_handles_github_error(self, mock_private_update, caplog):
        """GitHub API error is logged."""
        mock_private_update.message.text = "Test note"

        github_settings = {
            "owner": "testowner",
            "repo": "testrepo",
            "token": "ghp_testtoken",
        }

        responses.add(
            responses.PUT,
            re.compile(
                r"https://api\.github\.com/repos/testowner/testrepo/contents/income/.+"
            ),
            json={"message": "Bad credentials"},
            status=401,
        )

        with patch(
            "src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)
        ):
            await add_short_note_to_obsidian(mock_private_update)

        assert len(responses.calls) == 1

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

    @responses.activate
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

        responses.add(
            responses.PUT,
            re.compile(
                r"https://api\.github\.com/repos/testowner/testrepo/contents/income/.+"
            ),
            json={"content": {"name": "test.md"}},
            status=201,
        )

        with patch(
            "src.obsidian.get_github_settings", AsyncMock(return_value=github_settings)
        ):
            await add_short_note_to_obsidian(mock_private_update)

        request_body = responses.calls[0].request.body
        import json

        body = json.loads(request_body)
        assert body["content"] == expected_base64
