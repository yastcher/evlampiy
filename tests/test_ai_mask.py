"""PII masking at the LLM boundary (src.ai._mask + ai_client._ai_complete)."""

import re
from unittest.mock import patch

from src.ai._mask import mask, unmask
from src.ai_client import classify_text

# A "dirty" segment: name (RU), phone, email, name (Latin).
_DIRTY = (
    "Иван Петров просил перезвонить на +7 905 123-45-67 "
    "или написать на ivan.petrov@example.com. John Smith тоже в копии."
)


class TestMaskRoundTrip:
    def test_unmask_restores_original(self):
        masked, mapping = mask(_DIRTY)
        assert unmask(masked, mapping) == _DIRTY

    def test_text_without_pii_is_unchanged(self):
        clean = "позвони завтра в обед и обсудим задачу по проекту"
        masked, mapping = mask(clean)
        assert masked == clean
        assert mapping == {}


class TestMaskSmoke:
    def test_phone_is_removed(self):
        masked, _ = mask(_DIRTY)
        assert "+7" not in masked
        assert "123-45-67" not in masked

    def test_email_is_removed(self):
        masked, _ = mask(_DIRTY)
        assert "@" not in masked

    def test_no_consecutive_capitalized_words_remain(self):
        masked, _ = mask(_DIRTY)
        assert re.search(r"[A-ZА-ЯЁ][a-zа-яё]+\s+[A-ZА-ЯЁ][a-zа-яё]+", masked) is None  # noqa: RUF001


class TestMaskTokens:
    def test_each_pii_category_gets_its_token(self):
        masked, _ = mask(_DIRTY)
        assert "<EMAIL_1>" in masked
        assert "<PHONE_1>" in masked
        assert "<NAME_1>" in masked
        assert "<NAME_2>" in masked  # two distinct names

    def test_repeated_pii_reuses_one_token(self):
        text = "напиши на a@b.com и продублируй на a@b.com"
        masked, mapping = mask(text)
        assert masked.count("<EMAIL_1>") == 2
        assert list(mapping.keys()) == ["<EMAIL_1>"]
        assert unmask(masked, mapping) == text


class TestMaskingAtBoundary:
    """End-to-end: `_ai_complete` masks the outgoing prompt and unmasks the result."""

    async def test_prompt_masked_outgoing_and_result_unmasked(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        # The LLM echoes the placeholder token back, as cleanup would preserve it.
        api_response = {"candidates": [{"content": {"parts": [{"text": "перезвонить <NAME_1>"}]}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(api_response, 200)

        prompt = "перезвонить Иван Петров на +7 905 123-45-67, email ivan@example.com"
        with (
            patch("src.ai_client.settings.gemini_api_key", "test-key"),
            patch("src.ai_client.settings.categorization_provider", "gemini"),
        ):
            result = await classify_text(prompt)

        # 1) The outgoing payload carries no PII — only placeholder tokens.
        sent_text = mock_ai_http.post.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
        assert "@" not in sent_text
        assert "+7" not in sent_text
        assert "Иван Петров" not in sent_text
        assert "<NAME_1>" in sent_text

        # 2) The result is unmasked — the token is restored to the real name.
        assert result == "перезвонить Иван Петров"
