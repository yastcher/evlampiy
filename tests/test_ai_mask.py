"""PII masking at the LLM boundary (evlampiy.ai._mask + ai_client._ai_complete)."""

import json
import re
from unittest.mock import patch

from evlampiy.ai._mask import Masker, mask, unmask
from evlampiy.ai_chat import chat_complete
from evlampiy.ai_client import classify_text

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


class TestOneMaskerForAChat:
    def test_the_same_pii_keeps_its_token_and_new_pii_continues_the_numbering(self):
        """A chat goes out as many messages: one person stays one token across them."""
        masker = Masker()

        first, second = masker.mask("позвони Иван Петров"), masker.mask("Иван Петров и Анна Смирнова")

        assert (first, second, masker.mapping) == (
            "позвони <NAME_1>",
            "<NAME_1> и <NAME_2>",
            {"<NAME_1>": "Иван Петров", "<NAME_2>": "Анна Смирнова"},
        )


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
            patch("evlampiy.ai_client.settings.gemini_api_key", "test-key"),
            patch("evlampiy.ai_client.settings.categorization_provider", "gemini"),
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


# What must never leave in a chat request: names, a phone, an email.
_CHAT_PII = ("Иван Петров", "John Smith", "Анна Смирнова", "+7", "@")


def _chat_with_pii() -> list[dict]:
    """A GPT chat's history: the question, a tool call the model made, and the note it found."""
    call = {
        "id": "tc_1",
        "type": "function",
        "function": {"name": "search_notes", "arguments": '{"query": "Анна Смирнова"}'},
    }
    return [
        {"role": "system", "content": "Be helpful"},
        {"role": "user", "content": _DIRTY},
        {"role": "assistant", "tool_calls": [call]},
        {"role": "tool", "tool_call_id": "tc_1", "name": "search_notes", "content": "Анна Смирнова: +7 916 000-00-00"},
    ]


class TestMaskingAtTheChatBoundary:
    """`ai_chat.chat_complete`, the GPT chat's one way out to every provider, sends tokens and gives back words."""

    async def test_no_pii_leaves_in_the_request(self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter):
        reply = {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(reply, 200)

        with patch("evlampiy.ai_client.settings.deepseek_api_key", "test-key"):
            await chat_complete(["deepseek"], _chat_with_pii())

        sent = json.dumps(mock_ai_http.post.call_args.kwargs["json"], ensure_ascii=False)
        assert [pii for pii in _CHAT_PII if pii in sent] == []

    async def test_the_callers_history_keeps_the_users_words(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        reply = {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(reply, 200)
        messages = _chat_with_pii()

        with patch("evlampiy.ai_client.settings.deepseek_api_key", "test-key"):
            await chat_complete(["deepseek"], messages)

        assert messages == _chat_with_pii()

    async def test_the_reply_comes_back_in_the_users_words(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        reply = {"choices": [{"message": {"role": "assistant", "content": "Перезвони <NAME_1> на <PHONE_1>"}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(reply, 200)

        with patch("evlampiy.ai_client.settings.deepseek_api_key", "test-key"):
            result = await chat_complete(["deepseek"], [{"role": "user", "content": "Иван Петров, +7 905 123-45-67"}])

        assert result is not None
        restored = "Перезвони Иван Петров на +7 905 123-45-67"
        assert (result.content, result.raw_message["content"]) == (restored, restored)

    async def test_a_tool_call_comes_back_in_the_users_words(
        self, mock_httpx_response_factory, mock_ai_http, mock_rate_limiter
    ):
        call = {
            "id": "tc_2",
            "type": "function",
            "function": {"name": "search_notes", "arguments": '{"query": "<NAME_1>"}'},
        }
        reply = {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [call]}}]}
        mock_ai_http.post.return_value = mock_httpx_response_factory(reply, 200)

        with patch("evlampiy.ai_client.settings.deepseek_api_key", "test-key"):
            result = await chat_complete(["deepseek"], [{"role": "user", "content": "найди Иван Петров"}])

        assert result is not None
        restored = '{"query": "Иван Петров"}'
        assert (result.tool_calls[0].arguments, result.raw_message["tool_calls"][0]["function"]["arguments"]) == (
            restored,
            restored,
        )
