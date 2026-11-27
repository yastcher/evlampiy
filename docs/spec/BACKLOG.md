# Backlog

What is decided to do and not done yet. An item that is done leaves this list in the same
change; one that turns into work of its own gets a spec in `docs/spec/`.

## Speech recognition

- **Understand a voice message that mixes Russian, English and Spanish.** Wit.ai cannot: it
  has an app per language, picked by the chat's language. In a probe on mixed-language samples,
  Groq Whisper without a forced language wrote a message wholly in another language in that
  language, where today's call (`language` = the chat's) translated it, and left Russian as it
  was; a switch of language by whole phrases inside one message held in none of its variants.
  To settle first:
  - which recognizer: availability, price and quality on mixed speech, Spanish included;
  - no self-hosted recognizer;
  - dropping `language` from the Groq call goes with this work;
  - the cleanup prompt says "Preserve the original language", singular: it may translate or
    "fix" a foreign phrase whatever the recognizer.
- **A failed recognition answers nothing.** The Groq client turns an error into an empty text,
  and both channels then return without a reply (`telegram/handlers/voice.py:111`); the
  self-test shows "returned empty", not why.
- **Wit.ai's chunks are glued without a space.** Audio goes to Wit.ai in 19.5 s chunks whose
  texts are joined with `+=` (`transcription/service.py:77`), so the words at every seam merge;
  on the free tier no LLM cleanup splits them.

## Operations

- **Hear when the bot is down.** Nothing tells the owner that the bot is down, and the bot
  cannot report its own death: the alarm has to live outside it. Two ways, the owner's call:
  - a dead man's switch (a healthchecks.io-style URL): the bot pings it every few minutes after
    a round trip to MongoDB, and silence raises the alarm — catches a dead bot, a dead database
    and a dead server alike;
  - an outside probe of `/health`, which then has to ask MongoDB too (today it answers without
    it: `deploy/common.sh`).
- **The deploy starts the database before the dump.** `deploy/deploy.sh` refuses a release
  while MongoDB is stopped, because `backup-db.sh` cannot dump it. Run
  `docker compose up -d --no-recreate --wait mongodb` before the dump: a stopped database no
  longer blocks a release, and the dump stays mandatory.

## Notes

- **A group chat's own vault** (asked by the owner). Today a group's note goes to the vault of
  whoever sent the voice message (`settings_chat_id` = `u_<sender>`), and a sender without one
  saves nothing (`test_group_uses_sender_settings`, `test_group_no_sender_settings_skips`).
  Wanted: a group connects a vault of its own, and its notes go there. To settle first:
  - who connects and disconnects it — a chat admin only?
  - whose GitHub token it is: the connecting admin's, so everyone in the group writes into
    that admin's repository through the bot;
  - the group's vault instead of the sender's, or both;
  - cleanup, language and auto-sort: the group's chat settings or the sender's (tokens stay
    the sender's: they hang on the user id);
  - the group's vault gathers several people's voice notes (152-FZ): say so when connecting.
- **The note's date is not ISO 8601.** `obsidian.py` writes `date: {now.isoformat()}Z`, and a
  UTC-aware time already ends in `+00:00`, so the note gets `…+00:00Z`; Obsidian and YAML may
  read it as a string, not a date.

## Code and tests

- **Dead or display-only code**: the `seconds_per_token` setting is never read;
  `groq_audio_daily_limit` is only shown in `/stats`; `ai_client.gpt_chat` is called by tests
  only; `grant_initial_credits_if_eligible` and `UsedTrial` are never called.
- **Revenue of early payments**: payments made before v0.10.0 recorded no Stars, so `/stats`
  shows less revenue for a month that had them.
- **Coverage sits on its floor**: 91.5968% against `fail_under = 91.6`, passing by the
  two-digit rounding; pytest-cov's summary line still prints "FAIL" (it compares unrounded).
- **Mutation survivors**: 194 survived and 49 untested in the v0.10.0 run
  (`uv run mutmut browse`); go through them and bring the ratchet's maximums down.

## Showcase

- **CONTRIBUTING and a pull request template**: how to run the gate, where CHANGELOG entries
  go, what a pull request needs before review.
