from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.github_api import get_or_create_obsidian_repo, put_github_file

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


class TestGetOrCreateObsidianRepo:
    """Test repo creation/check."""

    async def test_returns_existing_repo(self):
        """Returns info when repo already exists."""
        user_response = _mock_httpx_response({"login": "testuser"}, 200)
        repo_response = _mock_httpx_response(status_code=200)

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [user_response, repo_response]
            _setup_async_client(mock_client_cls, mock_client)

            result = await get_or_create_obsidian_repo("ghp_token")

        assert result == {"owner": "testuser", "repo": "obsidian-notes", "token": "ghp_token"}

    async def test_creates_new_repo(self):
        """Creates repo when it doesn't exist."""
        user_response = _mock_httpx_response({"login": "testuser"}, 200)
        not_found_response = _mock_httpx_response(status_code=404)
        create_response = _mock_httpx_response(status_code=201)
        gitkeep_response = _mock_httpx_response(status_code=201)

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [user_response, not_found_response]
            mock_client.post.return_value = create_response
            mock_client.put.return_value = gitkeep_response
            _setup_async_client(mock_client_cls, mock_client)

            result = await get_or_create_obsidian_repo("ghp_token")

        assert result == {"owner": "testuser", "repo": "obsidian-notes", "token": "ghp_token"}
        mock_client.post.assert_called_once()
        mock_client.put.assert_called_once()

    async def test_returns_none_on_invalid_token(self):
        """Returns None when GitHub token is invalid."""
        user_response = _mock_httpx_response({"message": "Bad credentials"}, 401)

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = user_response
            _setup_async_client(mock_client_cls, mock_client)

            result = await get_or_create_obsidian_repo("invalid_token")

        assert result is None


class TestPutGithubFile:
    """Test file creation in GitHub."""

    async def test_creates_file_successfully(self):
        """File is created in GitHub repo."""
        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.put.return_value = _mock_httpx_response(status_code=201)
            _setup_async_client(mock_client_cls, mock_client)

            result = await put_github_file(
                token="ghp_token",
                owner="testuser",
                repo="testrepo",
                path="income/test.md",
                content="Hello",
                commit_message="test commit",
            )

        assert result is True

    async def test_returns_false_on_auth_error(self):
        """Returns False on 401 without retry."""
        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.put.return_value = _mock_httpx_response(status_code=401)
            _setup_async_client(mock_client_cls, mock_client)

            result = await put_github_file(
                token="bad_token",
                owner="testuser",
                repo="testrepo",
                path="income/test.md",
                content="Hello",
                commit_message="test commit",
            )

        assert result is False
        mock_client.put.assert_called_once()
