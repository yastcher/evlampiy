"""PII masking for outgoing LLM payloads (152-ФЗ).

Voice notes and user text carry third-party personal data — phones, emails, names.
Before any of it leaves for an external LLM, this module replaces that PII with
placeholder tokens (`<PHONE_N>`, `<EMAIL_N>`, `<NAME_N>`) and restores it in the
response. It is applied where each LLM client hands a request to its providers, never
per-provider: `ai_client._ai_complete` for one prompt (cleanup, categorization) and
`ai_chat.chat_complete` for the GPT chat, whose history carries the user's question,
the model's tool calls and the notes the tools found.

The token→original map lives only for the duration of one request and is built and
consumed inside those two functions, so callers (Obsidian save, chat reply) only ever
see the restored, unmasked text — and the provider only ever sees tokens.
"""

import re
import typing
from collections.abc import Callable, Mapping, Sequence

# Phone: optional +, a lead digit, then 7+ digit/separator chars, ending in a digit.
# Catches "+7 905 123 45 67", "89051234567", "+7(905)123-45-67".
_PHONE_RE = re.compile(r"\+?\d[\d ()\-.]{7,}\d")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Two or more consecutive capitalized words (Cyrillic or Latin) — ФИО.
_NAME_RE = re.compile(r"[A-ZА-ЯЁ][a-zа-яё]+(?:\s+[A-ZА-ЯЁ][a-zа-яё]+)+")  # noqa: RUF001 — Cyrillic ranges are intentional

# Order matters: emails and phones first, so the name pass never sees their characters.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL", _EMAIL_RE),
    ("PHONE", _PHONE_RE),
    ("NAME", _NAME_RE),
)


class Masker:
    """Masks the texts of one request with one set of tokens.

    The same PII keeps its token from text to text and new PII continues the numbering, so
    a chat sent as many messages reads consistently, and `mapping` restores any part of the
    reply.
    """

    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}  # token → original
        self._tokens: dict[str, str] = {}  # original → token, to dedupe repeats
        self._counters: dict[str, int] = {}

    def mask(self, text: str) -> str:
        """`text` with its PII replaced by this request's tokens."""
        for label, pattern in _PATTERNS:
            text = pattern.sub(self._replacer(label), text)
        return text

    def _replacer(self, label: str) -> Callable[[re.Match[str]], str]:
        def repl(match: re.Match[str]) -> str:
            original = match.group(0)
            token = self._tokens.get(original)
            if token is None:
                self._counters[label] = self._counters.get(label, 0) + 1
                token = f"<{label}_{self._counters[label]}>"
                self._tokens[original] = token
                self.mapping[token] = original
            return token

        return repl


def mask(text: str) -> tuple[str, dict[str, str]]:
    """Replace PII with placeholder tokens.

    Returns ``(masked_text, mapping)`` where ``mapping`` is token→original. Identical PII
    reuses the same token so the LLM sees a consistent placeholder.
    """
    masker = Masker()
    return masker.mask(text), masker.mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    """Restore original PII from a token→original map produced by :func:`mask`.

    The ``>`` terminator in each token prevents prefix collisions (``<NAME_1>`` is not a
    substring of ``<NAME_10>``), so a plain per-token replace is unambiguous.
    """
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text


def mask_messages(messages: Sequence[Mapping[str, typing.Any]], masker: Masker) -> list[dict[str, typing.Any]]:
    """A chat's messages (OpenAI's format) as they may leave: every text and every tool call's arguments masked.

    Copies, so the caller's history keeps the user's words.
    """
    return [_with_texts(message, masker.mask) for message in messages]


def unmask_message(message: Mapping[str, typing.Any], mapping: dict[str, str]) -> dict[str, typing.Any]:
    """A chat message (OpenAI's format) with its text and its tool calls' arguments restored."""
    return _with_texts(message, lambda text: unmask(text, mapping))


def _with_texts(message: Mapping[str, typing.Any], change: Callable[[str], str]) -> dict[str, typing.Any]:
    """A copy of `message` with `change` applied to its text and to each tool call's arguments, a JSON string."""
    copy = dict(message)
    if isinstance(copy.get("content"), str):
        copy["content"] = change(copy["content"])
    if copy.get("tool_calls"):
        copy["tool_calls"] = [
            {**call, "function": {**call["function"], "arguments": change(call["function"]["arguments"])}}
            if isinstance(call.get("function", {}).get("arguments"), str)
            else call
            for call in copy["tool_calls"]
        ]
    return copy
