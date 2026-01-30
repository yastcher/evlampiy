from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.categorization import (
    categorize_all_income,
    categorize_note,
    classify_note,
    get_existing_categories,
    move_github_file,
)

pytestmark = [pytest.mark.asyncio]


def _mock_httpx_response(json_data=None, status_code=200):
    response = MagicMock()
    response.json.return_value = json_data or {}
    response.status_code = status_code
    return response


def _setup_async_client(mock_client_cls, mock_client):
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client


class TestGetExistingCategories:
    """Test category listing from GitHub repo."""

    async def test_filters_excluded_categories(self):
        """income and trash folders are excluded from categories."""
        mock_contents = [
            {"name": "income", "type": "dir"},
            {"name": "trash", "type": "dir"},
            {"name": "work", "type": "dir"},
            {"name": "personal", "type": "dir"},
            {"name": "README.md", "type": "file"},
        ]

        with patch(
            "src.categorization.get_repo_contents", AsyncMock(return_value=mock_contents)
        ):
            result = await get_existing_categories("token", "owner", "repo")

        assert "income" not in result
        assert "trash" not in result
        assert "work" in result
        assert "personal" in result
        assert len(result) == 2

    async def test_returns_empty_list_on_empty_repo(self):
        """Returns empty list when no categories exist."""
        with patch("src.categorization.get_repo_contents", AsyncMock(return_value=[])):
            result = await get_existing_categories("token", "owner", "repo")

        assert result == []


class TestClassifyNote:
    """Test note classification with Claude API."""

    async def test_returns_existing_category(self):
        """Returns existing category when note matches."""
        api_response = {
            "content": [{"text": "work"}],
        }

        with (
            patch("src.categorization.settings.anthropic_api_key", "test-key"),
            patch("src.categorization.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_httpx_response(api_response, 200)
            _setup_async_client(mock_client_cls, mock_client)

            result = await classify_note("Meeting notes about project X", ["work", "personal"])

        assert result == "work"

    async def test_suggests_new_category(self):
        """Suggests new category name when no match."""
        api_response = {
            "content": [{"text": "health_fitness"}],
        }

        with (
            patch("src.categorization.settings.anthropic_api_key", "test-key"),
            patch("src.categorization.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_httpx_response(api_response, 200)
            _setup_async_client(mock_client_cls, mock_client)

            result = await classify_note("Gym workout plan", ["work", "personal"])

        assert result == "health_fitness"

    async def test_returns_none_without_api_key(self):
        """Returns None when API key not configured."""
        with patch("src.categorization.settings.anthropic_api_key", ""):
            result = await classify_note("Some text", ["work"])

        assert result is None

    async def test_normalizes_category_name(self):
        """Converts spaces to underscores and lowercases."""
        api_response = {
            "content": [{"text": "Health Fitness"}],
        }

        with (
            patch("src.categorization.settings.anthropic_api_key", "test-key"),
            patch("src.categorization.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_httpx_response(api_response, 200)
            _setup_async_client(mock_client_cls, mock_client)

            result = await classify_note("Workout notes", [])

        assert result == "health_fitness"

    async def test_returns_none_on_api_error(self):
        """Returns None when Anthropic API fails."""
        with (
            patch("src.categorization.settings.anthropic_api_key", "test-key"),
            patch("src.categorization.httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_httpx_response(status_code=500)
            _setup_async_client(mock_client_cls, mock_client)

            result = await classify_note("Some text", ["work"])

        assert result is None


class TestMoveGithubFile:
    """Test file move operation in GitHub."""

    async def test_moves_file_successfully(self):
        """File is moved by copying and deleting."""
        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha123")),
            ),
            patch("src.categorization.put_github_file", AsyncMock(return_value=True)),
            patch("src.categorization.delete_github_file", AsyncMock(return_value=True)),
        ):
            result = await move_github_file(
                "token", "owner", "repo", "income/note.md", "work/note.md"
            )

        assert result is True

    async def test_returns_false_when_file_not_found(self):
        """Returns False when source file doesn't exist."""
        with patch("src.categorization.get_github_file", AsyncMock(return_value=None)):
            result = await move_github_file(
                "token", "owner", "repo", "income/note.md", "work/note.md"
            )

        assert result is False

    async def test_returns_false_when_copy_fails(self):
        """Returns False when put_github_file fails."""
        with (
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha123")),
            ),
            patch("src.categorization.put_github_file", AsyncMock(return_value=False)),
        ):
            result = await move_github_file(
                "token", "owner", "repo", "income/note.md", "work/note.md"
            )

        assert result is False


class TestCategorizeNote:
    """Test single note categorization."""

    async def test_categorizes_and_moves_note(self):
        """Note is classified and moved to category folder."""
        with (
            patch(
                "src.categorization.get_existing_categories",
                AsyncMock(return_value=["work", "personal"]),
            ),
            patch("src.categorization.classify_note", AsyncMock(return_value="work")),
            patch("src.categorization.move_github_file", AsyncMock(return_value=True)),
        ):
            result = await categorize_note(
                "token", "owner", "repo", "note.md", "Meeting notes"
            )

        assert result == "work"

    async def test_returns_none_when_classification_fails(self):
        """Returns None when classification fails."""
        with (
            patch("src.categorization.get_existing_categories", AsyncMock(return_value=[])),
            patch("src.categorization.classify_note", AsyncMock(return_value=None)),
        ):
            result = await categorize_note(
                "token", "owner", "repo", "note.md", "Some content"
            )

        assert result is None


class TestCategorizeAllIncome:
    """Test batch categorization of income folder."""

    async def test_processes_markdown_files(self):
        """Processes .md files and skips others."""
        mock_contents = [
            {"name": "note1.md", "type": "file"},
            {"name": "note2.md", "type": "file"},
            {"name": ".gitkeep", "type": "file"},
            {"name": "subfolder", "type": "dir"},
        ]

        with (
            patch(
                "src.categorization.get_repo_contents", AsyncMock(return_value=mock_contents)
            ),
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha")),
            ),
            patch("src.categorization.categorize_note", AsyncMock(return_value="work")),
        ):
            result = await categorize_all_income("token", "owner", "repo")

        assert result == 2

    async def test_returns_zero_on_empty_folder(self):
        """Returns 0 when income folder is empty."""
        with patch("src.categorization.get_repo_contents", AsyncMock(return_value=[])):
            result = await categorize_all_income("token", "owner", "repo")

        assert result == 0

    async def test_counts_only_successful_categorizations(self):
        """Only counts successfully categorized files."""
        mock_contents = [
            {"name": "note1.md", "type": "file"},
            {"name": "note2.md", "type": "file"},
        ]

        with (
            patch(
                "src.categorization.get_repo_contents", AsyncMock(return_value=mock_contents)
            ),
            patch(
                "src.categorization.get_github_file",
                AsyncMock(return_value=("content", "sha")),
            ),
            patch(
                "src.categorization.categorize_note",
                AsyncMock(side_effect=["work", None]),
            ),
        ):
            result = await categorize_all_income("token", "owner", "repo")

        assert result == 1
