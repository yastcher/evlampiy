"""Unit tests for transcript cleanup via LLM."""

from unittest.mock import AsyncMock, patch

from src.transcript_cleanup import cleanup_transcript


class TestCleanupTranscript:
    """Test cleanup_transcript function."""

    async def test_short_text_returned_without_llm(self):
        """Text shorter than 20 chars is returned as-is without calling LLM."""
        with patch("src.transcript_cleanup.cleanup_text") as mock_cleanup:
            result = await cleanup_transcript("short text")
            assert result == "short text"
            mock_cleanup.assert_not_called()

    async def test_successful_cleanup_returns_llm_response(self):
        """Successful LLM call returns cleaned text."""
        original = "ну вот значит я хотел сказать что вот этот вот проект он типа классный"
        cleaned = "Я хотел сказать, что этот проект классный."

        with patch(
            "src.transcript_cleanup.cleanup_text",
            AsyncMock(return_value=cleaned),
        ):
            result = await cleanup_transcript(original)
            assert result == cleaned

    async def test_llm_error_returns_original_text(self):
        """LLM exception returns original text."""
        original = "ну вот значит я хотел сказать что этот проект классный"

        with patch(
            "src.transcript_cleanup.cleanup_text",
            AsyncMock(side_effect=RuntimeError("API error")),
        ):
            result = await cleanup_transcript(original)
            assert result == original

    async def test_empty_llm_response_returns_original_text(self):
        """Empty LLM response returns original text."""
        original = "ну вот значит я хотел сказать что этот проект классный"

        with patch(
            "src.transcript_cleanup.cleanup_text",
            AsyncMock(return_value=""),
        ):
            result = await cleanup_transcript(original)
            assert result == original

    async def test_none_llm_response_returns_original_text(self):
        """None LLM response returns original text."""
        original = "ну вот значит я хотел сказать что этот проект классный"

        with patch(
            "src.transcript_cleanup.cleanup_text",
            AsyncMock(return_value=None),
        ):
            result = await cleanup_transcript(original)
            assert result == original
