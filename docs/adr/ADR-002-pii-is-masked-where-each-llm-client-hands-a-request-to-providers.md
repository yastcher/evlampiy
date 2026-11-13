# ADR-002 — PII is masked where each LLM client hands a request to its providers

**Status:** accepted 2026-11-12 (`ai/_mask.py`: `Masker`, `mask_messages`,
`unmask_message`; `ai_client._ai_complete`; `ai_chat.chat_complete`).

**Context.** Voice notes and user text carry the names, phones and emails of third parties,
and 152-ФЗ keeps them from external LLMs in plain text. Two clients talk to the providers:
`ai_client` sends one prompt (cleanup, categorization); `ai_chat` sends the GPT chat, a
history of the question, the model's tool calls and the notes the tools found. Until
2026-11-12 only the first was masked.

**Decision.**
- Masking happens in the two functions where a request leaves for the providers, never
  per provider.
- The chat masks its whole history with one `Masker`, one set of tokens per request, and
  restores the reply's text, its tool calls' arguments and the message kept for history;
  the caller's history keeps the user's words.
- The token map lives in memory for one request.

**Why.**
- One place per client covers every provider of its chain, and every fallback, by
  construction.
- Masking each message on its own would give two people the same token.
- A history stored masked would mix tokens of different requests.

**Consequences.** A new way to an LLM goes through one of the two functions (AGENTS.md says
so). The name pattern also catches two capitalized words that are not a name, in the
instructions as well: a known limit of a regex mask.
