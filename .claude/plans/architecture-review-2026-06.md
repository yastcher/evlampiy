# Architecture review — production-readiness gaps (2026-06)

Critical review of the current architecture against industry best practices for a
production product. Grounded in the code as of v0.9.2. Strengths (kept for context):
framework-agnostic `services/*`, thin `telegram/handlers/*` + `whatsapp/*` adapters,
architecture tests enforcing layer isolation, unified `ai_client` with fallback chains.

The findings below are mostly **latent** — invisible at the current near-zero user count,
but they break under concurrency or growth. Fixes are deliberately proportional (no Celery,
no new datastore, no saga framework) per the project's "simplest thing that works" rule.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done.

---

## P0 — blocking work in the shared event loop  `[x]`

**Where:** `src/transcription/service.py:18-22` (`get_audio_duration_seconds`),
`:57-77` (`_transcribe_with_wit`); `src/transcription/wit_client.py` (sync `wit.Wit`).

`transcribe_audio` is `async` but synchronously calls:

- `AudioSegment.from_file(...)` / `chunk.export(format="mp3")` — blocking ffmpeg subprocess
  (decode + per-chunk conversion);
- `translator.speech(...)` — the `wit` library is synchronous (requests), one blocking HTTP
  round-trip per 19.5s chunk.

`grep to_thread|run_in_executor` over `src/` → none. All of this runs in the single event
loop that also serves Telegram polling and the WhatsApp FastAPI webhook (`src/main.py:32-36`).

**Impact:** one minute of audio = 3+ blocking ffmpeg conversions + 3+ synchronous HTTP calls,
during which the whole process is frozen — other users wait, Meta webhook deliveries time out
and retry (dupes), polling stalls. Effective throughput under concurrency ≈ 1.

**Fix:** wrap the blocking sync functions in `asyncio.to_thread(...)` inside `transcribe_audio`
(both `get_audio_duration_seconds` and `_transcribe_with_wit`). The Groq path is already async
(httpx, no ffmpeg) and stays as-is. Single-file change, no new layer.

**Test:** behavioral reproduction — run `transcribe_audio` (with the sync path stubbed to
`time.sleep`) concurrently with a 10ms async "ticker"; assert the ticker keeps advancing
(loop stays responsive). Fails before the fix (ticker frozen), passes after.

---

## P0 — no MongoDB indexes on hot query fields  `[x]`

**Done:** added `indexes` to every model in `src/dto.py` (unique on natural keys: `chat_id`,
`user_id`, `(user_id, month_key)`, `(role, user_id)`, `(month_key, language)`, `key`,
`user_hash`, `month_key`, `(alert_type, month_key)`, `whatsapp_phone`; non-unique lookup
indexes on `LinkCode`/`AccountLink`/`RecentTranscription`). Added a race-safe `get_or_create`
helper in `src/mongo.py` (catches `DuplicateKeyError` on the lost insert, re-fetches the
winner) and routed all find-then-insert sites through it (mongo/credits/wit_tracking/alerts/
account_linking). Note: this prevents duplicate *documents*; atomic `$inc` against lost
*updates* is still P1.

**Where:** `src/dto.py` — only `RecentTranscription:172` has an index (TTL). `UserSettings`,
`UserCredits`, `UserRole`, `UserMonthlyUsage`, `LinkCode`, `AccountLink`, `WitUsageStats`,
`MonthlyStats` have none. No `unique=True` anywhere.

`UserSettings` is queried by `chat_id` 6-8× per message (`get_chat_language`, `get_gpt_command`,
`get_preferred_provider`, `get_save_to_obsidian`, `get_auto_cleanup`, `get_auto_categorize`,
`get_github_settings`); `has_role` runs several times per message. All full collection scans.

No unique index ⇒ the check-then-act `get_or_create_user` (`src/mongo.py:50-56`) and
`_get_or_create_user_credits` create **duplicate documents** under concurrent first-touch.

**Fix:** add `indexes` to each model's `class Settings` (unique on `UserSettings.chat_id`,
`UserCredits.user_id`, `UserMonthlyUsage [(user_id, month_key)]`; non-unique on
`UserRole [(user_id), (role)]`, `LinkCode.code`). Beanie builds them on `init_beanie`.

---

## P1 — money: non-atomic balance mutations (lost update)  `[x]`

**Done:** balance/counter mutations are now atomic. `deduct_credits` uses a single
aggregation-pipeline `update_one` (free-first, floored at 0, monthly reset inline);
`add_credits`/`admin_add_credits`/stat counters use `find_one(...).upsert(Inc(...),
on_insert=...)`. `get_credits` is a pure read (effective free computed, persisted lazily on
next spend), so reads can't clobber a deduction; `_ensure_fresh_free_credits` removed. Note:
mongomock serializes ops so the race itself isn't unit-testable — atomicity is validated by
design + functional tests; the deduct return split is derived from the pre-snapshot (balance
stays exact, split is stats-only). The cost-preauthorization gap (`voice.py:134` hardcoded
cost=1) is NOT addressed here.

**Where:** `src/credits.py:171-195` (`deduct_credits`), `:133-151` (`add_credits`), all
`increment_*`/`record_*`. All read-modify-write via Beanie `.save()` (full-doc write). No
`$inc`, no optimistic locking (revision), no transactions (`grep` → none).

Concurrent voice messages from one user → both read the same balance, both write → lost
deduction (free transcription); stats undercount.

**Fix:** atomic `$inc` via Beanie `.inc({...})` / `find_one_and_update`. For free→purchased
split, conditional update or a short Mongo transaction.

**Adjacent:** no cost pre-authorization (`src/telegram/handlers/voice.py:134` checks
`can_perform_operation(user_id, 1)` with hardcoded cost=1; real cost deducted post-hoc with
`overdraft` allowed). Check/deduct on actual `duration` before the expensive LLM cleanup.

---

## P1 — payment not idempotent  `[x]`

**Done:** new `ProcessedPayment` doc (unique index on `charge_id`). `award_tokens` claims the
charge id first (insert; `DuplicateKeyError` ⇒ already processed → returns `None`), so a
redelivered `successful_payment` never double-credits; the handler skips re-credit/re-notify
on `None`. Claim-first is deliberate: prefer a rare recoverable claimed-but-uncredited crash
window over silently granting paid tokens twice.

**Where:** `src/telegram/handlers/payments.py:79-92` → `src/services/payments_service.py:57-74`.
`award_tokens` credits with no dedup on `successful_payment.telegram_payment_charge_id`.
Telegram can redeliver the same `successful_payment` → double-credit of real Stars.

**Fix:** insert a `ProcessedPayment(charge_id)` with a unique index before crediting; duplicate
key ⇒ already processed, return. Idempotency key.

---

## P1 — single process: shared fate + scaling ceiling  `[ ]`

**Where:** `src/main.py:32-36` — Telegram polling + uvicorn/FastAPI + WhatsApp in one asyncio
process via `TaskGroup`.

- Any non-`TelegramNetworkError` from `run_bot` cancels siblings and kills the process
  (crash-loop under `restart: always`). Retry only catches network errors
  (`src/telegram/setup.py:230`).
- No horizontal scaling: long-polling is single-consumer; in-memory `RateLimiter` and httpx
  singleton are per-process.

**Fix (proportional):** supervise the subsystems independently so one's failure restarts only
itself instead of fail-fast tearing down the group; document "single instance" as a constraint.

---

## P1 — health/readiness practically absent  `[x]`

**Done:** `serve_fastapi` now always starts (`main.py` no longer gates it on WhatsApp config),
so `/health` answers regardless; `docker-compose.yml` has a `curl`-based healthcheck on the app
container. Caveat documented in `docs/DEPLOY.md`: plain Compose reports health but doesn't
restart unhealthy containers (needs an orchestrator/autoheal sidecar).

**Where:** `src/whatsapp/app.py:24-26` — `/health` exists only when WhatsApp is configured
(FastAPI starts only then, `main.py:34`). `docker-compose.yml` has no healthcheck on the app
container (only mongodb). `restart: always` catches process exit, not a wedged loop.

**Fix:** always serve a minimal `/health`; add a compose healthcheck.

---

## P1 — GitHub token at rest + over-broad scope  `[ ]`

**Where:** `src/mongo.py:85-92` stores the OAuth token as plaintext `github_settings.token`;
`src/github_oauth.py:13` requests scope `repo` (full r/w to all repos). One DB read = full
GitHub control for every connected user.

**Fix:** encrypt the token at rest with an app key (envelope); minimize requested scope /
consider fine-grained PAT flow.

---

## P1 — PII to third-party LLMs unmasked (cross-cutting)  `[~]`

**Done (cleanup + categorization):** `src/ai/_mask.py` masks phones/emails/names to
`<PHONE_N>`/`<EMAIL_N>`/`<NAME_N>` at the single chokepoint `ai_client._ai_complete` (covers
`cleanup_text`, `classify_text`, `gpt_chat`) and unmasks the response; in-memory per-request
map. Optional `LOG_LLM_PAYLOADS` logs the masked payload at DEBUG. Tests: round-trip + smoke
(`tests/test_ai_mask.py`) + boundary integration (`TestPiiMaskingBoundary`).

**Remaining:** `src/ai_chat.py` (the tool-calling `/evlampiy` path) makes its own `client.post`
calls bypassing `_ai_complete`, so its message arrays + tool results (note text fetched by
`get_recent_notes`) are still sent in plaintext. Masking it needs message-level mask/unmask
with a mapping that persists across the multi-turn tool loop — a separate, larger change.

---

## P2 — structural  `[ ]`

- God-object `Settings` (`src/config.py:22`, 40+ fields) contradicts the project's own
  "split BaseSettings per module".
- Repeated `UserSettings` reads (6-8 queries of one doc per message) — fetch once, pass down;
  compounds the missing indexes.
- No migration strategy: deprecated fields, "empty for legacy records" — schema drift on a
  document DB without versioning.
- No graceful shutdown of shared resources: `close_client()` (`ai_client.py:113`) is never
  called; httpx pool and Mongo client not closed on SIGTERM.
- No observability beyond logs (`grep sentry|prometheus|otel` → none).

---

## Recommended order

1. `asyncio.to_thread` around ffmpeg+wit — biggest impact, smallest diff. **(P0, done)**
2. Indexes + unique in Beanie models — kills full scans and duplicate-doc race. **(P0, done)**
3. Atomic `$inc` for balances + payment idempotency by `charge_id` — money correctness. **(P1, done)**
4. Always-on `/health` + compose healthcheck. **(P1, done)**
5. PII masking in `ai_client`. **(P1, done for cleanup/categorization; `ai_chat` tool-calling path remaining)**
6. Token encryption; supervised subsystems; split Settings. (P1/P2)
