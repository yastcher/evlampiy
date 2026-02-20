"""Unit tests for transcript cleanup via LLM."""

from unittest.mock import AsyncMock, patch

from src.transcript_cleanup import _build_cleanup_prompt, cleanup_transcript


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

    async def test_vocabulary_included_in_prompt(self):
        """Domain vocabulary is appended to the prompt when provided."""
        text = "ну я занимаюсь кантоу и вот типа тренировка была"
        vocabulary = {"sports": ["кантоу", "тренировка"]}
        captured_prompts = []

        async def capture(prompt, max_tokens):
            captured_prompts.append(prompt)
            return "cleaned"

        with patch("src.transcript_cleanup.cleanup_text", side_effect=capture):
            await cleanup_transcript(text, vocabulary=vocabulary)

        assert len(captured_prompts) == 1
        assert "кантоу" in captured_prompts[0]
        assert "тренировка" in captured_prompts[0]
        assert "Domain vocabulary" in captured_prompts[0]

    async def test_context_included_in_prompt(self):
        """Recent context notes are appended to the prompt when provided."""
        text = "ну и сегодня про то же самое"
        context = ["Вчера рассказывал про проект X.", "Обсуждали дедлайн на пятницу."]
        captured_prompts = []

        async def capture(prompt, max_tokens):
            captured_prompts.append(prompt)
            return "cleaned"

        with patch("src.transcript_cleanup.cleanup_text", side_effect=capture):
            await cleanup_transcript(text, context=context)

        assert len(captured_prompts) == 1
        assert "проект X" in captured_prompts[0]
        assert "Context from recent notes" in captured_prompts[0]

    async def test_no_context_no_vocabulary_prompt_has_no_extra_sections(self):
        """Prompt with no extras contains no Context or Vocabulary sections."""
        prompt = _build_cleanup_prompt("some text here", vocabulary=None, context=None)
        assert "Context from recent" not in prompt
        assert "Domain vocabulary" not in prompt
        assert "Transcription:\nsome text here" in prompt

    async def test_empty_context_list_not_included(self):
        """Empty context list does not add a context section to the prompt."""
        prompt = _build_cleanup_prompt("some text here", vocabulary=None, context=[])
        assert "Context from recent" not in prompt
