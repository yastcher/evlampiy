"""Tests for transcription provider selection logic."""

from unittest.mock import patch

from src import const
from src.dto import UserTier
from src.telegram.voice import _select_provider


class TestSelectProvider:
    """Test transcription provider selection logic."""

    def test_vip_gets_wit_by_default(self):
        """VIP user gets Wit by default (auto), not Groq."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.VIP, wit_available=True)

        assert result == const.PROVIDER_WIT

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


class TestSelectProviderWithPreference:
    """Test provider selection with user's preferred_provider."""

    def test_paid_auto_wit_available(self):
        """Paid + preferred=None + wit available -> WIT (auto)."""
        result = _select_provider(UserTier.PAID, wit_available=True)
        assert result == const.PROVIDER_WIT

    def test_paid_auto_wit_unavailable_groq_configured(self):
        """Paid + preferred=None + wit unavailable + groq configured -> GROQ (fallback)."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.PAID, wit_available=False)
        assert result == const.PROVIDER_GROQ

    def test_paid_preferred_groq_configured(self):
        """Paid + preferred=groq + groq configured -> GROQ."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.PAID, wit_available=True, preferred_provider="groq")
        assert result == const.PROVIDER_GROQ

    def test_paid_preferred_groq_not_configured(self):
        """Paid + preferred=groq + groq not configured + wit available -> WIT (fallback)."""
        with patch("src.telegram.voice.settings.groq_api_key", ""):
            result = _select_provider(UserTier.PAID, wit_available=True, preferred_provider="groq")
        assert result == const.PROVIDER_WIT

    def test_paid_preferred_wit_available(self):
        """Paid + preferred=wit + wit available -> WIT."""
        result = _select_provider(UserTier.PAID, wit_available=True, preferred_provider="wit")
        assert result == const.PROVIDER_WIT

    def test_paid_preferred_wit_unavailable_groq_fallback(self):
        """Paid + preferred=wit + wit unavailable + groq configured -> GROQ (fallback)."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.PAID, wit_available=False, preferred_provider="wit")
        assert result == const.PROVIDER_GROQ

    def test_free_preferred_groq_ignored(self):
        """Free + preferred=groq -> ignored, WIT (auto)."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.FREE, wit_available=True, preferred_provider="groq")
        assert result == const.PROVIDER_WIT

    def test_free_wit_unavailable_returns_none(self):
        """Free + wit unavailable -> None (Free never gets Groq)."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.FREE, wit_available=False, preferred_provider="groq")
        assert result is None

    def test_vip_auto_wit_available(self):
        """VIP + preferred=None + wit available -> WIT (default changed)."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.VIP, wit_available=True)
        assert result == const.PROVIDER_WIT

    def test_vip_preferred_groq_configured(self):
        """VIP + preferred=groq + groq configured -> GROQ."""
        with patch("src.telegram.voice.settings.groq_api_key", "test-key"):
            result = _select_provider(UserTier.VIP, wit_available=True, preferred_provider="groq")
        assert result == const.PROVIDER_GROQ

    def test_tester_auto_wit_available(self):
        """Tester + preferred=None + wit available -> WIT."""
        result = _select_provider(UserTier.TESTER, wit_available=True)
        assert result == const.PROVIDER_WIT
