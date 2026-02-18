"""Tests for rate limiter, retry logic, and provider fallback."""

import os
from unittest.mock import patch

import pytest

from src import const
from src.ai_client import (
    RateLimiter,
    classify_text,
)


class TestRateLimiterThrottles:
    """Test that the rate limiter enforces RPM limits."""

    async def test_rate_limiter_throttles(self, capture_ai_sleep):
        """Rate limiter sleeps when token bucket is exhausted."""
        limiter = RateLimiter({"test": 2})  # 2 RPM → 2 initial tokens

        # First two calls consume the initial tokens
        await limiter.acquire("test")
        await limiter.acquire("test")
        # Third call must sleep — bucket is empty
        await limiter.acquire("test")

        assert len(capture_ai_sleep) >= 1, "Rate limiter should have slept at least once"
        assert capture_ai_sleep[0] > 0, "Sleep duration must be positive"

    async def test_rate_limiter_skips_unknown_provider(self, capture_ai_sleep):
        """acquire() on unknown provider returns immediately without sleeping."""
        limiter = RateLimiter({"test": 1})

        await limiter.acquire("unknown_provider")

        assert capture_ai_sleep == []

    async def test_rate_limiter_refills_over_time(self, capture_ai_sleep):
        """Tokens refill based on elapsed time between calls."""
        limiter = RateLimiter({"test": 60})  # 60 RPM = 1 token/sec

        # Drain all 60 initial tokens
        for _ in range(60):
            await limiter.acquire("test")
        # No real time has passed → next call must sleep
        await limiter.acquire("test")

        assert len(capture_ai_sleep) >= 1


class TestRetryOn429:
    """Test retry behavior on 429 rate-limit responses."""

    async def test_retry_on_429_succeeds(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, mock_ai_sleep
    ):
        """Provider is retried on 429 and returns result on second attempt."""
        ok_response = mock_httpx_response_factory(
            {"candidates": [{"content": {"parts": [{"text": "result"}]}}]}, 200
        )
        rate_limited = mock_httpx_response_factory(status_code=429)
        mock_ai_http.post.side_effect = [rate_limited, ok_response]

        with (
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test")

        assert result == "result"
        assert mock_ai_http.post.call_count == 2

    async def test_retry_on_429_three_attempts(
        self,
        mock_httpx_response_factory,
        mock_ai_http,
        mock_rate_limiter,
        no_fallback_keys,
        capture_ai_sleep,
    ):
        """Provider retries exactly 3 times before exhausting, sleeps between attempts."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=429)

        with (
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test")

        assert result is None
        # 3 attempts total → 2 sleeps between them (delays: 2s, 4s)
        assert mock_ai_http.post.call_count == 3
        assert len(capture_ai_sleep) == 2
        assert capture_ai_sleep[0] == 2.0
        assert capture_ai_sleep[1] == 4.0


class TestFallbackOnExhausted:
    """Test fallback chain when primary provider is rate-limited."""

    async def test_fallback_to_groq_on_gemini_429(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, mock_ai_sleep
    ):
        """When Gemini exhausts retries on 429, request falls back to Groq."""
        gemini_429 = mock_httpx_response_factory(status_code=429)
        groq_ok = mock_httpx_response_factory(
            {"choices": [{"message": {"content": "groq_result"}}]}, 200
        )

        async def fake_post(url: str, **kwargs):
            if "generateContent" in url:
                return gemini_429
            if "groq" in url:
                return groq_ok
            return mock_httpx_response_factory(status_code=404)

        mock_ai_http.post.side_effect = fake_post

        with (
            patch("src.ai_client.settings.gemini_api_key", "gemini-key"),
            patch("src.ai_client.settings.groq_api_key", "groq-key"),
            patch("src.ai_client.settings.openrouter_api_key", ""),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test")

        assert result == "groq_result"
        # Gemini called 3 times (retries), then Groq 1 time
        assert mock_ai_http.post.call_count == 4

    async def test_all_providers_exhausted_returns_none(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter, mock_ai_sleep
    ):
        """Returns None when all providers in chain are exhausted."""
        mock_ai_http.post.return_value = mock_httpx_response_factory(status_code=429)

        with (
            patch("src.ai_client.settings.gemini_api_key", "gemini-key"),
            patch("src.ai_client.settings.groq_api_key", "groq-key"),
            patch("src.ai_client.settings.openrouter_api_key", "openrouter-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text("Test")

        assert result is None


@pytest.mark.skipif(
    not os.getenv("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping integration test",
)
class TestGroqIntegration:
    """Integration test with real Groq API."""

    async def test_groq_complete(self):
        """Groq LLM returns a valid response to classify prompt."""
        with (
            patch("src.ai_client.settings.groq_api_key", os.getenv("GROQ_API_KEY", "")),
            patch("src.ai_client.settings.categorization_provider", const.PROVIDER_GROQ),
        ):
            result = await classify_text("Say only the word: hello")

        assert result is not None
        assert len(result) > 0


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set — skipping integration test",
)
class TestOpenRouterIntegration:
    """Integration test with real OpenRouter API."""

    async def test_openrouter_complete(self):
        """OpenRouter returns a valid response to classify prompt."""
        with (
            patch(
                "src.ai_client.settings.openrouter_api_key",
                os.getenv("OPENROUTER_API_KEY", ""),
            ),
            patch("src.ai_client.settings.categorization_provider", const.PROVIDER_OPENROUTER),
        ):
            result = await classify_text("Say only the word: hello")

        assert result is not None
        assert len(result) > 0
