from unittest.mock import patch

import httpx

from src.ai_client import (
    _api_base,
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

    async def test_gemini_returns_text(self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter):
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
        ok_response = mock_httpx_response_factory({"candidates": [{"content": {"parts": [{"text": "work"}]}}]}, 200)
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

    async def test_anthropic_returns_text(self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter):
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

    async def test_openai_returns_text(self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter):
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

    async def test_gpt_chat_uses_gpt_provider(self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter):
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

    async def test_strips_backticks_from_response(self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter):
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


class TestFallbackOnNetworkError:
    """Test fallback chain when provider hits network errors."""

    async def test_http_error_falls_back_to_next_provider(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, mock_ai_sleep
    ):
        """httpx.HTTPError on primary → falls back to secondary provider."""

        groq_ok = mock_httpx_response_factory({"choices": [{"message": {"content": "groq_result"}}]}, 200)

        call_count = 0

        async def fake_post(url: str, **kwargs):
            nonlocal call_count
            call_count += 1
            if "generativelanguage" in url:
                raise httpx.ConnectError("Connection refused")
            if "groq" in url:
                return groq_ok
            return mock_httpx_response_factory(status_code=404)

        mock_ai_http.post.side_effect = fake_post

        with (
            patch("src.ai_client.settings.gemini_api_key", "gemini-key"),
            patch("src.ai_client.settings.groq_api_key", "groq-key"),
            patch("src.ai_client.settings.openrouter_api_key", ""),
            patch("src.ai_client.settings.deepseek_api_key", ""),
            patch("src.ai_client.settings.qwen_api_key", ""),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test")

        assert result == "groq_result"
        # Gemini fails on first call (no retries for HTTPError), then Groq succeeds
        assert call_count == 2

    async def test_empty_response_falls_back_to_next_provider(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, mock_ai_sleep
    ):
        """Provider returns empty text → falls back to next provider."""
        empty_gemini = mock_httpx_response_factory({"candidates": [{"content": {"parts": [{"text": ""}]}}]}, 200)
        groq_ok = mock_httpx_response_factory({"choices": [{"message": {"content": "groq_result"}}]}, 200)

        async def fake_post(url: str, **kwargs):
            if "generativelanguage" in url:
                return empty_gemini
            if "groq" in url:
                return groq_ok
            return mock_httpx_response_factory(status_code=404)

        mock_ai_http.post.side_effect = fake_post

        with (
            patch("src.ai_client.settings.gemini_api_key", "gemini-key"),
            patch("src.ai_client.settings.groq_api_key", "groq-key"),
            patch("src.ai_client.settings.openrouter_api_key", ""),
            patch("src.ai_client.settings.deepseek_api_key", ""),
            patch("src.ai_client.settings.qwen_api_key", ""),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test")

        assert result == "groq_result"


class TestApiBase:
    """Test LLM-proxy base resolution (_api_base)."""

    def test_proxies_groq_when_base_set(self):
        with patch("src.ai_client.settings.llm_api_base", "https://proxy.example"):
            assert _api_base("groq", "https://api.groq.com") == "https://proxy.example/groq"

    def test_proxies_gemini_when_base_set(self):
        with patch("src.ai_client.settings.llm_api_base", "https://proxy.example"):
            base = _api_base("gemini", "https://generativelanguage.googleapis.com")
            assert base == "https://proxy.example/gemini"

    def test_does_not_proxy_deepseek(self):
        # DeepSeek is reachable directly, so it keeps its own base even with a proxy set.
        with patch("src.ai_client.settings.llm_api_base", "https://proxy.example"):
            assert _api_base("deepseek", "https://api.deepseek.com/v1") == "https://api.deepseek.com/v1"

    def test_returns_default_when_base_empty(self):
        with patch("src.ai_client.settings.llm_api_base", ""):
            assert _api_base("groq", "https://api.groq.com") == "https://api.groq.com"


class TestLlmProxyRouting:
    """The configured LLM proxy base rewrites the outgoing request URL."""

    async def test_gemini_request_goes_through_proxy(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        api_response = {"candidates": [{"content": {"parts": [{"text": "work"}]}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        with (
            patch("src.ai_client.settings.llm_api_base", "https://proxy.example"),
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.gemini_model", "gemini-2.0-flash"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test prompt")

        assert result == "work"
        posted_url = mock_ai_http.post.call_args.args[0]
        assert posted_url == "https://proxy.example/gemini/v1beta/models/gemini-2.0-flash:generateContent"

    async def test_deepseek_request_bypasses_proxy(self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter):
        api_response = {"choices": [{"message": {"content": "work"}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        with (
            patch("src.ai_client.settings.llm_api_base", "https://proxy.example"),
            patch("src.ai_client.settings.deepseek_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "deepseek"),
        ):
            result = await classify_text("Test prompt")

        assert result == "work"
        posted_url = mock_ai_http.post.call_args.args[0]
        assert posted_url == "https://api.deepseek.com/v1/chat/completions"
