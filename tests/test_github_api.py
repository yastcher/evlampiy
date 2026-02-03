import base64
from unittest.mock import patch

from src.github_api import (
    delete_github_file,
    get_github_file,
    get_or_create_obsidian_repo,
    get_repo_contents,
    put_github_file,
)


class TestGetOrCreateObsidianRepo:
    """Test repo creation/check."""

    async def test_returns_existing_repo(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns info when repo already exists."""
        user_response = mock_httpx_response_factory({"login": "testuser"}, 200)
        repo_response = mock_httpx_response_factory(status_code=200)

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.get.side_effect = [user_response, repo_response]

            result = await get_or_create_obsidian_repo("ghp_token")

        assert result == {"owner": "testuser", "repo": "obsidian-notes", "token": "ghp_token"}

    async def test_creates_new_repo(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Creates repo when it doesn't exist."""
        user_response = mock_httpx_response_factory({"login": "testuser"}, 200)
        not_found_response = mock_httpx_response_factory(status_code=404)
        create_response = mock_httpx_response_factory(status_code=201)
        gitkeep_response = mock_httpx_response_factory(status_code=201)

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.get.side_effect = [user_response, not_found_response]
            mock_client.post.return_value = create_response
            mock_client.put.return_value = gitkeep_response

            result = await get_or_create_obsidian_repo("ghp_token")

        assert result == {"owner": "testuser", "repo": "obsidian-notes", "token": "ghp_token"}
        mock_client.post.assert_called_once()
        mock_client.put.assert_called_once()

    async def test_returns_none_on_invalid_token(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns None when GitHub token is invalid."""
        user_response = mock_httpx_response_factory({"message": "Bad credentials"}, 401)

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.get.return_value = user_response

            result = await get_or_create_obsidian_repo("invalid_token")

        assert result is None


class TestPutGithubFile:
    """Test file creation in GitHub."""

    async def test_creates_file_successfully(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """File is created in GitHub repo."""
        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.put.return_value = mock_httpx_response_factory(status_code=201)

            result = await put_github_file(
                token="ghp_token",
                owner="testuser",
                repo="testrepo",
                path="income/test.md",
                content="Hello",
                commit_message="test commit",
            )

        assert result is True

    async def test_returns_false_on_auth_error(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns False on 401 without retry."""
        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.put.return_value = mock_httpx_response_factory(status_code=401)

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


class TestGetRepoContents:
    """Test repo contents listing."""

    async def test_returns_list_of_contents(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns list of files and folders."""
        contents = [
            {"name": "income", "type": "dir"},
            {"name": "README.md", "type": "file"},
        ]

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.get.return_value = mock_httpx_response_factory(contents, 200)

            result = await get_repo_contents("ghp_token", "owner", "repo")

        assert len(result) == 2
        assert result[0]["name"] == "income"

    async def test_returns_single_item_as_list(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns single item wrapped in list."""
        single_file = {"name": "README.md", "type": "file"}

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.get.return_value = mock_httpx_response_factory(single_file, 200)

            result = await get_repo_contents("ghp_token", "owner", "repo", "README.md")

        assert len(result) == 1

    async def test_returns_empty_list_on_error(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns empty list on error."""
        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.get.return_value = mock_httpx_response_factory(status_code=404)

            result = await get_repo_contents("ghp_token", "owner", "repo")

        assert result == []


class TestGetGithubFile:
    """Test file content retrieval."""

    async def test_returns_content_and_sha(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns decoded content and SHA."""
        content = "Hello World"
        encoded = base64.b64encode(content.encode()).decode()
        response_data = {"content": encoded, "sha": "abc123"}

        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.get.return_value = mock_httpx_response_factory(response_data, 200)

            result = await get_github_file("ghp_token", "owner", "repo", "path/file.md")

        assert result is not None
        assert result[0] == "Hello World"
        assert result[1] == "abc123"

    async def test_returns_none_on_not_found(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns None when file not found."""
        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.get.return_value = mock_httpx_response_factory(status_code=404)

            result = await get_github_file("ghp_token", "owner", "repo", "nonexistent.md")

        assert result is None


class TestDeleteGithubFile:
    """Test file deletion."""

    async def test_deletes_file_successfully(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns True on successful delete."""
        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.delete.return_value = mock_httpx_response_factory(status_code=200)

            result = await delete_github_file(
                "ghp_token", "owner", "repo", "path/file.md", "sha123", "Delete file"
            )

        assert result is True

    async def test_returns_false_on_error(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Returns False on error."""
        with patch("src.github_api.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.delete.return_value = mock_httpx_response_factory(status_code=404)

            result = await delete_github_file(
                "ghp_token", "owner", "repo", "nonexistent.md", "sha123", "Delete"
            )

        assert result is False
