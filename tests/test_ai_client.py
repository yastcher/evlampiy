from unittest.mock import patch

from src.ai_client import (
    _strip_backticks,
    classify_text,
    gpt_chat,
)


class TestStripBackticks:
    """Test markdown code block stripping."""

    def test_strips_backticks(self):
        assert _strip_backticks("```\nwork\n```") == "work"

    def test_returns_plain_text(self):
        assert _strip_backticks("work") == "work"

    def test_strips_whitespace(self):
        assert _strip_backticks("  work  ") == "work"


class TestGeminiProvider:
    """Test Gemini provider HTTP calls."""

    async def test_gemini_returns_text(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """Gemini provider returns parsed text."""
        api_response = {
            "candidates": [{"content": {"parts": [{"text": "work"}]}}],
        }
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        with (
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test prompt")

        assert result == "work"

    async def test_gemini_returns_none_without_key(self, mock_rate_limiter, no_fallback_keys):
        """Returns None when Gemini key not set."""
        with patch("src.ai_client.settings.categorization_provider", "gemini"):
            result = await classify_text("Test prompt")

        assert result is None

    async def test_gemini_empty_candidates(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, no_fallback_keys
    ):
        """Returns None on empty candidates."""
        mock_ai_http.post.return_value = mock_httpx_response_factory({"candidates": []}, 200)

        with (
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test prompt")

        assert result is None

    async def test_gemini_api_error(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, no_fallback_keys
    ):
        """Returns None on API error."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=500)

        with (
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test prompt")

        assert result is None

    async def test_gemini_retries_on_429(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, mock_ai_sleep
    ):
        """Gemini retries after 429 and succeeds on next attempt."""
        ok_response = mock_httpx_response_factory(
            {"candidates": [{"content": {"parts": [{"text": "work"}]}}]}, 200
        )
        rate_limited = mock_httpx_response_factory(status_code=429)
        mock_ai_http.post.side_effect = [rate_limited, ok_response]

        with (
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test prompt")

        assert result == "work"

    async def test_gemini_exhausts_retries_on_429(
        self,
        mock_httpx_response_factory,
        mock_ai_http,
        mock_rate_limiter,
        mock_ai_sleep,
        no_fallback_keys,
    ):
        """Gemini returns None after exhausting all retries on 429."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=429)

        with (
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test prompt")

        assert result is None


class TestAnthropicProvider:
    """Test Anthropic provider HTTP calls."""

    async def test_anthropic_returns_text(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """Anthropic provider returns parsed text."""
        api_response = {
            "content": [{"text": "work"}],
        }
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        with (
            patch("src.ai_client.settings.anthropic_bot_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "anthropic"),
        ):
            result = await classify_text("Test prompt")

        assert result == "work"

    async def test_anthropic_returns_none_without_key(self, mock_rate_limiter, no_fallback_keys):
        """Returns None when Anthropic key not set."""
        with patch("src.ai_client.settings.categorization_provider", "anthropic"):
            result = await classify_text("Test prompt")

        assert result is None

    async def test_anthropic_api_error(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, no_fallback_keys
    ):
        """Returns None on Anthropic API error."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=500)

        with (
            patch("src.ai_client.settings.anthropic_bot_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "anthropic"),
        ):
            result = await classify_text("Test prompt")

        assert result is None


class TestOpenAIProvider:
    """Test OpenAI provider HTTP calls."""

    async def test_openai_returns_text(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """OpenAI provider returns parsed text."""
        api_response = {
            "choices": [{"message": {"content": "work"}}],
        }
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        with (
            patch("src.ai_client.settings.gpt_token", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "openai"),
        ):
            result = await classify_text("Test prompt")

        assert result == "work"

    async def test_openai_returns_none_without_key(self, mock_rate_limiter, no_fallback_keys):
        """Returns None when OpenAI key not set."""
        with patch("src.ai_client.settings.categorization_provider", "openai"):
            result = await classify_text("Test prompt")

        assert result is None

    async def test_openai_api_error(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, no_fallback_keys
    ):
        """Returns None on OpenAI API error."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=500)

        with (
            patch("src.ai_client.settings.gpt_token", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "openai"),
        ):
            result = await classify_text("Test prompt")

        assert result is None


class TestProviderDispatch:
    """Test provider dispatch and gpt_chat function."""

    async def test_unknown_provider_returns_none(self, mock_rate_limiter, no_fallback_keys):
        """Returns None for unknown provider."""
        with patch("src.ai_client.settings.categorization_provider", "unknown"):
            result = await classify_text("Test")

        assert result is None

    async def test_gpt_chat_uses_gpt_provider(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """gpt_chat dispatches to gpt_provider setting."""
        api_response = {
            "candidates": [{"content": {"parts": [{"text": "Hello!"}]}}],
        }
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        with (
            patch("src.ai_client.settings.gpt_provider", "gemini"),
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
        ):
            result = await gpt_chat("Hello")

        assert result == "Hello!"

    async def test_strips_backticks_from_response(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        """Strips markdown backticks from provider response."""
        api_response = {
            "candidates": [{"content": {"parts": [{"text": "```\nwork\n```"}]}}],
        }
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        with (
            patch("src.ai_client.settings.categorization_provider", "gemini"),
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
        ):
            result = await classify_text("Test")

        assert result == "work"
