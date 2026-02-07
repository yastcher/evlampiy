"""Tests for transcription provider selection logic."""

from unittest.mock import patch

from src import const
from src.dto import UserTier
from src.telegram.voice import _select_provider


class TestSelectProvider:
    """Test transcription provider selection logic."""

    def test_vip_gets_groq_when_configured(self):
        """VIP user gets Groq when API key is set."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.VIP, wit_available=True)

        assert result == const.PROVIDER_GROQ

    def test_vip_gets_wit_without_groq(self):
        """VIP user falls back to Wit when Groq not configured."""
        with patch("src.telegram.voice.settings.groq_api_key", ""):
            result = _select_provider(UserTier.VIP, wit_available=True)

        assert result == const.PROVIDER_WIT

    def test_free_user_gets_wit_when_available(self):
        """Free user gets Wit when it's available."""
        result = _select_provider(UserTier.FREE, wit_available=True)

        assert result == const.PROVIDER_WIT

    def test_free_user_gets_none_when_wit_exhausted(self):
        """Free user gets None when Wit is exhausted."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.FREE, wit_available=False)

        assert result is None

    def test_paid_user_gets_wit_when_available(self):
        """Paid user prefers Wit when it's available."""
        result = _select_provider(UserTier.PAID, wit_available=True)

        assert result == const.PROVIDER_WIT

    def test_paid_user_gets_groq_when_wit_exhausted(self):
        """Paid user gets Groq when Wit is exhausted."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.PAID, wit_available=False)

        assert result == const.PROVIDER_GROQ

    def test_paid_user_gets_none_when_no_providers(self):
        """Paid user gets None when both Wit exhausted and Groq not configured."""
        with patch("src.telegram.voice.settings.groq_api_key", ""):
            result = _select_provider(UserTier.PAID, wit_available=False)

        assert result is None

    def test_tester_gets_wit_when_available(self):
        """Tester gets Wit.ai as primary provider."""
        result = _select_provider(UserTier.TESTER, wit_available=True)

        assert result == const.PROVIDER_WIT

    def test_tester_gets_groq_fallback_when_wit_exhausted(self):
        """Tester falls back to Groq when Wit is exhausted."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.TESTER, wit_available=False)

        assert result == const.PROVIDER_GROQ

    def test_tester_gets_none_when_no_providers(self):
        """Tester gets None when Wit exhausted and Groq not configured."""
        with patch("src.telegram.voice.settings.groq_api_key", ""):
            result = _select_provider(UserTier.TESTER, wit_available=False)

        assert result is None
