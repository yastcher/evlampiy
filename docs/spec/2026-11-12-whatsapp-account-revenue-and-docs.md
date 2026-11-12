# WhatsApp as the linked account, revenue in Stars, docs that follow the code

Status: in progress, 2026-11-12. Decided with the owner: WhatsApp is the linked Telegram
account (ADR-001); the vocabulary promise is dropped; `GITHUB_TOKEN_SETUP.md` becomes the
operator's guide to the OAuth App.

## The request

Fix what the glossary pass found: WhatsApp skips the block check and Wit accounting,
`/stats` overstates revenue, revenue-milestone alerts never fire, `ai_chat.py` is over the
500-line limit, and about twenty places in the docs describe another bot than the code.

## Facts (checked in the code, 2026-11-12)

- WhatsApp (`whatsapp/handlers.py`) takes the linked Telegram user's tier and nothing else:
  no block check, no Wit cap (`is_wit_available`) and no Wit count (`increment_wit_usage`),
  no token check or charge (an unlinked number transcribes for free, without limit), no
  transcription stats. Language and vault are read for `wa_<phone>`, which nothing can set:
  the default language always, notes never saved.
- `docs/WHATSAPP_LINKING.md` promised that linking spends Telegram Stars credits on WhatsApp.
- `/stats` prints the tokens sold as "Stars received" and revenue as tokens ×
  `STAR_TO_DOLLAR`; packages sell up to 40 % more tokens than Stars. The Stars a payment
  brought are not stored anywhere.
- Revenue milestones are checked only inside the month's first-payment branch, and
  `check_and_send_alerts` also runs after every Wit transcription with `credits_just_sold=1`.
- `cleanup_transcript` has taken a `vocabulary` since it was written (`029de9f`), and no
  caller has ever passed one: only categorization reads `vocabulary.json`.
- `GITHUB_TOKEN_SETUP.md` explains a personal access token for a `settings.github_token`
  that does not exist; GitHub connects by OAuth Device Flow, which needs the operator's
  `GITHUB_CLIENT_ID`, and nothing explains how to get one.

## Decisions

- WhatsApp: ADR-001.
- Revenue: `MonthlyStats.total_stars`, raised by the Stars each payment brought; `/stats`
  and the milestones read it. Payments before this change left no Stars behind, so a month
  that had them shows less revenue than it took.
- Alerts: the payment alerts (the month's first payment, a milestone on any payment) run
  from the payment handler; the Wit alerts run after Wit use on either channel, through the
  bot the Telegram side registers at start.
- The vocabulary serves categorization only; the docs say so, and cleanup's parameter stays.
- `GITHUB_TOKEN_SETUP.md`: how to create the OAuth App, enable Device Flow and set
  `GITHUB_CLIENT_ID`, in the file's four languages.

## Steps, one commit each, tests first

1. Revenue in Stars; payment alerts and Wit alerts apart.
2. `services/voice_access.py`: one admission (block, tier, provider, wallet) and one
   settlement (charge, Wit and Groq use, stats) for both channels. Telegram moves onto it
   with its behaviour unchanged; WhatsApp follows ADR-001.
3. `ai_chat.py`: the provider formats (tool schemas, message conversion, response
   parsing) move to a module of their own, unchanged.
4. Docs: the drift list, the vocabulary promise, the OAuth App guide, WhatsApp per ADR-001.

## Not in this change

- Settings and functions nothing uses (`seconds_per_token`, `ai_client.gpt_chat`,
  `grant_initial_credits_if_eligible`): removing them is the owner's call.
- Re-running mutants the memory cap killed (insights inbox, 2026-11-12).
