from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.github_oauth import get_github_device_code, poll_github_for_token

pytestmark = [pytest.mark.asyncio]


def _mock_httpx_response(json_data, status_code=200):
    response = MagicMock()
    response.json.return_value = json_data
    response.status_code = status_code
    return response


def _setup_async_client(mock_client_cls, mock_client):
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_client


class TestGetGithubDeviceCode:
    """Test device code request."""

    async def test_returns_device_info(self):
        """Successful device code request."""
        expected = {
            "device_code": "abc123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }

        with patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_httpx_response(expected)
            _setup_async_client(mock_client_cls, mock_client)

            result = await get_github_device_code()

        assert result == expected


class TestPollGithubForToken:
    """Test OAuth token polling."""

    async def test_returns_token_on_success(self):
        """Token returned after successful authorization."""
        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_httpx_response({"access_token": "ghp_test_token"})
            _setup_async_client(mock_client_cls, mock_client)

            result = await poll_github_for_token(device_code="abc123", interval=5, expires_in=900)

        assert result == "ghp_test_token"

    async def test_returns_none_on_expired_token(self):
        """None returned when token expires."""
        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_httpx_response({"error": "expired_token"})
            _setup_async_client(mock_client_cls, mock_client)

            result = await poll_github_for_token(device_code="abc123", interval=5, expires_in=900)

        assert result is None

    async def test_returns_none_on_access_denied(self):
        """None returned when access is denied."""
        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = _mock_httpx_response({"error": "access_denied"})
            _setup_async_client(mock_client_cls, mock_client)

            result = await poll_github_for_token(device_code="abc123", interval=5, expires_in=900)

        assert result is None

    async def test_waits_on_authorization_pending(self):
        """Keeps polling when authorization is pending."""
        pending_response = _mock_httpx_response({"error": "authorization_pending"})
        success_response = _mock_httpx_response({"access_token": "ghp_final"})

        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_client = AsyncMock()
            mock_client.post.side_effect = [pending_response, success_response]
            _setup_async_client(mock_client_cls, mock_client)

            result = await poll_github_for_token(device_code="abc123", interval=5, expires_in=900)

        assert result == "ghp_final"
        assert mock_sleep.call_count == 2

    async def test_returns_none_on_timeout(self):
        """None returned when polling exceeds expires_in."""
        pending_response = _mock_httpx_response({"error": "authorization_pending"})

        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = pending_response
            _setup_async_client(mock_client_cls, mock_client)

            result = await poll_github_for_token(device_code="abc123", interval=10, expires_in=15)

        assert result is None
