"""Tests for evlampiy.services.stats_service.build_stats_text."""

from unittest.mock import AsyncMock, patch

from evlampiy.services.stats_service import build_stats_text


class TestBuildStatsWitStatus:
    """Test build_stats_text with Wit.ai at different usage levels."""

    async def test_wit_warning_threshold(self):
        """Wit.ai at 80% shows Warning status."""
        with (
            patch("evlampiy.services.stats_service.get_monthly_stats", AsyncMock(return_value=None)),
            patch(
                "evlampiy.services.stats_service.get_all_wit_usage_this_month",
                AsyncMock(return_value={"ru": 400}),
            ),
            patch("evlampiy.services.stats_service.settings.wit_free_monthly_limit", 500),
            patch("evlampiy.services.stats_service.settings.groq_api_key", ""),
            patch("evlampiy.services.stats_service.settings.gemini_api_key", ""),
            patch("evlampiy.services.stats_service.settings.anthropic_bot_api_key", ""),
            patch("evlampiy.services.stats_service.settings.openrouter_api_key", ""),
            patch("evlampiy.services.stats_service.settings.gpt_token", ""),
            patch("evlampiy.services.stats_service.settings.groq_audio_daily_limit", 7200),
            patch("evlampiy.services.stats_service.settings.categorization_provider", "deepseek"),
            patch("evlampiy.services.stats_service.settings.gpt_provider", "deepseek"),
            patch("evlampiy.services.stats_service.get_bot_config", AsyncMock(return_value="deepseek")),
        ):
            text = await build_stats_text()

        assert "Warning" in text

    async def test_wit_critical_threshold(self):
        """Wit.ai at 95% shows CRITICAL status."""
        with (
            patch("evlampiy.services.stats_service.get_monthly_stats", AsyncMock(return_value=None)),
            patch(
                "evlampiy.services.stats_service.get_all_wit_usage_this_month",
                AsyncMock(return_value={"ru": 475}),
            ),
            patch("evlampiy.services.stats_service.settings.wit_free_monthly_limit", 500),
            patch("evlampiy.services.stats_service.settings.groq_api_key", ""),
            patch("evlampiy.services.stats_service.settings.gemini_api_key", ""),
            patch("evlampiy.services.stats_service.settings.anthropic_bot_api_key", ""),
            patch("evlampiy.services.stats_service.settings.openrouter_api_key", ""),
            patch("evlampiy.services.stats_service.settings.gpt_token", ""),
            patch("evlampiy.services.stats_service.settings.groq_audio_daily_limit", 7200),
            patch("evlampiy.services.stats_service.settings.categorization_provider", "deepseek"),
            patch("evlampiy.services.stats_service.settings.gpt_provider", "deepseek"),
            patch("evlampiy.services.stats_service.get_bot_config", AsyncMock(return_value="deepseek")),
        ):
            text = await build_stats_text()

        assert "CRITICAL" in text

    async def test_wit_ok_status(self):
        """Wit.ai below 80% shows OK status."""
        with (
            patch("evlampiy.services.stats_service.get_monthly_stats", AsyncMock(return_value=None)),
            patch(
                "evlampiy.services.stats_service.get_all_wit_usage_this_month",
                AsyncMock(return_value={"ru": 100}),
            ),
            patch("evlampiy.services.stats_service.settings.wit_free_monthly_limit", 500),
            patch("evlampiy.services.stats_service.settings.groq_api_key", ""),
            patch("evlampiy.services.stats_service.settings.gemini_api_key", ""),
            patch("evlampiy.services.stats_service.settings.anthropic_bot_api_key", ""),
            patch("evlampiy.services.stats_service.settings.openrouter_api_key", ""),
            patch("evlampiy.services.stats_service.settings.gpt_token", ""),
            patch("evlampiy.services.stats_service.settings.groq_audio_daily_limit", 7200),
            patch("evlampiy.services.stats_service.settings.categorization_provider", "deepseek"),
            patch("evlampiy.services.stats_service.settings.gpt_provider", "deepseek"),
            patch("evlampiy.services.stats_service.get_bot_config", AsyncMock(return_value="deepseek")),
        ):
            text = await build_stats_text()

        assert "OK" in text
        assert "Warning" not in text
        assert "CRITICAL" not in text
