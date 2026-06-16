"""PII masking for outgoing LLM payloads (152-ФЗ).

Voice notes and user text carry third-party personal data — phones, emails, names.
Before any of it leaves for an external LLM (cleanup / categorization), this module
replaces that PII with placeholder tokens (`<PHONE_N>`, `<EMAIL_N>`, `<NAME_N>`) and
restores it in the response. It is applied at the single LLM-client boundary
(`ai_client._ai_complete`), never per-provider.

The token→original map lives only for the duration of one request: `mask` returns it and
`unmask` consumes it, both inside `_ai_complete`, so callers (Obsidian save, chat reply)
only ever see the restored, unmasked text — and the provider only ever sees tokens.
"""

import re

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


def mask(text: str) -> tuple[str, dict[str, str]]:
    """Replace PII with placeholder tokens.

    Returns ``(masked_text, mapping)`` where ``mapping`` is token→original. Identical PII
    reuses the same token so the LLM sees a consistent placeholder.
    """
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}  # original → token, to dedupe repeats
    counters: dict[str, int] = {}

    def _replacer(label: str):
        def repl(match: re.Match[str]) -> str:
            original = match.group(0)
            token = reverse.get(original)
            if token is None:
                counters[label] = counters.get(label, 0) + 1
                token = f"<{label}_{counters[label]}>"
                reverse[original] = token
                mapping[token] = original
            return token

        return repl

    for label, pattern in _PATTERNS:
        text = pattern.sub(_replacer(label), text)
    return text, mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    """Restore original PII from a token→original map produced by :func:`mask`.

    The ``>`` terminator in each token prevents prefix collisions (``<NAME_1>`` is not a
    substring of ``<NAME_10>``), so a plain per-token replace is unambiguous.
    """
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text
