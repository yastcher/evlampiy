# ADR-001 — WhatsApp is the linked Telegram account

**Status:** accepted 2026-11-12 (`services/voice_access.py`: `admit_voice`, `settle_voice`;
`whatsapp/handlers.py`: `handle_voice_message`).

**Context.** WhatsApp took the linked Telegram user's tier and nothing else: no block, no
token check or charge, no Wit cap or count, and settings read for a `wa_<phone>` chat that
nothing can set, so the default language always and notes never saved. An unlinked number
transcribed for free and without limit. The docs promised that linking spends the
Telegram Stars balance on WhatsApp.

**Decision.**
- A number linked with `/link_whatsapp` acts as that user's private Telegram chat: the
  block, the tier, the wallet (free monthly tokens first, then purchased ones; vip and
  tester unlimited) and the `u_<id>` settings (language, vault, cleanup, sorting).
- Both channels go through one admission and one settlement (`services/voice_access.py`).
- An unlinked number is told how to link and gets nothing else; `link <code>` works before
  any check.
- WhatsApp sells nothing: an empty balance is answered with a pointer to `/buy` in Telegram.

**Why.**
- Tokens are sold for Telegram Stars only. A free channel beside the paid one makes the paid
  one pointless, and its Wit requests come out of the monthly free limit everyone shares.
- Settings that cannot be set are not settings.
- One admission for both channels keeps a block, a tier or a price from holding on one
  channel only.

**Consequences.** WhatsApp needs a Telegram account, and the docs say so. A number cannot be
blocked on its own: blocking the linked Telegram user blocks it. Spec:
`docs/spec/2026-11-12-whatsapp-account-revenue-and-docs.md`.
