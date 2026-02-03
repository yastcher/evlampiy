from unittest.mock import AsyncMock, patch

from src.github_oauth import get_github_device_code, poll_github_for_token


class TestGetGithubDeviceCode:
    """Test device code request."""

    async def test_returns_device_info(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Successful device code request."""
        expected = {
            "device_code": "abc123",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "expires_in": 900,
            "interval": 5,
        }

        with patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls:
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.post.return_value = mock_httpx_response_factory(expected)

            result = await get_github_device_code()

        assert result == expected


class TestPollGithubForToken:
    """Test OAuth token polling."""

    async def test_returns_token_on_success(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Token returned after successful authorization."""
        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.post.return_value = mock_httpx_response_factory({"access_token": "ghp_test_token"})

            result = await poll_github_for_token(device_code="abc123", interval=5, expires_in=900)

        assert result == "ghp_test_token"

    async def test_returns_none_on_expired_token(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """None returned when token expires."""
        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.post.return_value = mock_httpx_response_factory({"error": "expired_token"})

            result = await poll_github_for_token(device_code="abc123", interval=5, expires_in=900)

        assert result is None

    async def test_returns_none_on_access_denied(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """None returned when access is denied."""
        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.post.return_value = mock_httpx_response_factory({"error": "access_denied"})

            result = await poll_github_for_token(device_code="abc123", interval=5, expires_in=900)

        assert result is None

    async def test_waits_on_authorization_pending(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """Keeps polling when authorization is pending."""
        pending_response = mock_httpx_response_factory({"error": "authorization_pending"})
        success_response = mock_httpx_response_factory({"access_token": "ghp_final"})

        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.post.side_effect = [pending_response, success_response]

            result = await poll_github_for_token(device_code="abc123", interval=5, expires_in=900)

        assert result == "ghp_final"
        assert mock_sleep.call_count == 2

    async def test_returns_none_on_timeout(self, mock_httpx_response_factory, mock_httpx_client_factory):
        """None returned when polling exceeds expires_in."""
        pending_response = mock_httpx_response_factory({"error": "authorization_pending"})

        with (
            patch("src.github_oauth.httpx.AsyncClient") as mock_client_cls,
            patch("src.github_oauth.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_client = mock_httpx_client_factory(mock_client_cls)
            mock_client.post.return_value = pending_response

            result = await poll_github_for_token(device_code="abc123", interval=10, expires_in=15)

        assert result is None
