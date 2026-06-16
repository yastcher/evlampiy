## [0.9.3] — 2026-06-16

### Added

- Always-on `/health` endpoint (served even without WhatsApp) plus a docker-compose healthcheck for the app container
- PII (phones/emails/names) is masked before cleanup/categorization prompts reach external LLMs and restored in the
  response, so personal data no longer leaves in plaintext (152-ФЗ); optional `LOG_LLM_PAYLOADS` logs the masked payload

### Fixed

- Transcription offloads ffmpeg decode + synchronous Wit.ai calls to a worker thread, so one voice note no longer
  freezes the event loop shared by all users and the WhatsApp webhook
- Concurrent first-touch no longer creates duplicate user/credit/stats documents — creation goes through a race-safe
  `get_or_create` backed by the unique indexes
- Credit balances and usage counters mutate via atomic `$inc`/pipeline updates instead of read-modify-write, so
  concurrent voice messages no longer lose deductions
- Telegram-Stars payments are idempotent (deduped by charge id) — a redelivered `successful_payment` no longer
  double-credits

## [0.9.2] — 2026-06-06

### Changed

- Notes now live under a configurable base dir (`OBSIDIAN_BASE_DIR`, default `evlampiy`): new notes land in
  `<base>/inbox`, categories under `<base>/`, never in the repo root
- Categorization strongly prefers existing categories and routes obvious garbage to `<base>/trash` (seeded on repo init)
- All MongoDB collections are now indexed on their query keys, with unique constraints on natural keys (was full
  collection scans on every message)

### Fixed

- Polling: `start_polling` retries on `TelegramNetworkError` with backoff instead of crashing the shared TaskGroup (and
  taking FastAPI/WhatsApp down with it)

## [0.9.1] — 2026-06-05

### Added

- Optional `TELEGRAM_API_BASE` to route the Bot API through a reverse proxy where `api.telegram.org` is blocked;
  Cloudflare Worker under `cloudflare/telegram-proxy/`

### Fixed

- `Settings` now ignores unknown env vars (`extra="ignore"`) so a `.env` shared with deploy tooling (`CLOUDFLARE_*`)
  no longer crashes startup
- Deploy: image name unified to `evlampiy_notes` across compose and CI (was mismatched, broke `docker compose up` with
  pull-access-denied)
- Deploy: SSH keepalive + `--remove-orphans` so the session survives the mongodb healthcheck wait (was `Broken pipe`,
  exit 255)
- OpenRouter default model → `google/gemma-4-31b-it:free` (old `gemma-3-27b-it:free` now returns 404, leaving cleanup
  silently uncleaned)
- Startup: a `TelegramNetworkError` from `set_my_commands` no longer crashes the whole app (shared TaskGroup) — command
  registration is now best-effort, polling starts regardless
- Self-test: voice upload is now best-effort, so a timed-out upload no longer swallows the text report

## [0.9.0] — 2026-04-13

### Added

- Bump script
- Architecture rule tests: `services/*` must not import aiogram / pywa / fastapi / src.telegram

### Fixed

- WhatsApp webhook init: `wa.setup_fastapi` does not exist in pywa; now `WhatsApp(server=app, ...)`
- MongoDB image pinned to `mongo:8.0.3`. Versions 8.0.5..8.0.20 and 8.2.x crash with SIGSEGV ~30s
  after startup on kernel 6.x + glibc 2.39+ hosts
- Selftest LLM-cleanup check now prepends `CLEANUP_PROMPT_BASE` (was sending raw text, false positive)
- Gemini-2.5 cleanup truncation: `thinkingConfig.thinkingBudget=0` disables hidden thinking-tokens

### Changed

- Telegram framework: python-telegram-bot v22 → aiogram v3.27
- WhatsApp framework: `pywa.WhatsApp` → `pywa_async.WhatsApp` (handlers became `await`-native)
- FastAPI runner: threading.Thread → `asyncio.TaskGroup` (single event loop)
- Type checker: mypy → ty (Astral)
- aiohttp pinned `>=3.13.4` (CVE)
- Architecture isolation roadmap (`.claude/plans/architecture-isolation.md`, PR1–PR7) closed:
  added `src/services/{stats,voice_pipeline,notes,settings,admin,payments,account_linking}_service.py`
  framework-agnostic services; `src/telegram/handlers/` is now a package with thin adapters per
  domain; `tests/{services,telegram}/` mirror the split; PTB-compat aliases removed from
  `tests/fixtures.py`

## [0.8.13] — 2026-04-13

### Added

- GPT tool calling for `/evlampiy` command: LLM can call `get_recent_notes`, `get_user_settings`, `get_categories`
  to answer based on real user data. Supports all 7 providers (OpenAI-compatible, Gemini, Anthropic)
- Strict mypy type checking (`strict = true`) with per-module overrides for untyped third-party libraries
- Bot-sender guard: `TypeHandler` at group=-1 rejects all updates from Telegram bot accounts via `effective_user.is_bot`
- PTB handler guards

### Changed

- `src/telegram/handlers.py` (774→217 lines): split into `settings_handlers.py`, `obsidian_handlers.py`,
  `account_handlers.py` by domain hub boundaries. Core routing stays in `handlers.py`
- Dockerfile: layer-cached dependency install via `uv.lock` (`--frozen --no-dev`), uv from official image
- `ai_client.py`: `global _http_client` replaced with `_HttpClientHolder` class
- `uv run mypy src` added as a required step in GitHub Actions CI pipeline
- `src/prompts.py`: LLM prompt strings centralized into a single module
- `src/types.py`: domain TypeAlias (`UserId`, `ChatId`, `MonthKey`, `Language`)
- Input parameters with `list[X]` replaced by `Sequence[X]` where the function does not mutate the collection;
  `dict[K,V]` replaced by `Mapping[K,V]` where only read

### Docs

- Architecture documentation (`docs/ARCHITECTURE.md`) and docs reorganization

## [0.8.12] — 2026-02-22

### Fixed

- DeepSeek API (`deepseek-chat`) added as primary AI provider for cleanup and categorization
- Qwen (Alibaba DashScope international) added as AI provider; fallback chain: deepseek → qwen → openrouter → gemini →
  groq
- "Setup Obsidian" button in `/obsidian` hub: creates `.obsidian/plugins/obsidian-git/data.json` in the repo with
  auto-pull pre-configured
- Empty response from AI provider (e.g. DeepSeek R1 returns empty `content`) now falls through to next provider in chain
  instead of silently stopping
- HTTP read timeout reduced to 45s per request to prevent reasoning models from stalling the chain for minutes
- Qwen removed from default fallback chain (config/implementation kept for manual selection)
- `no_fallback_keys` test fixture now also clears `deepseek_api_key` and `qwen_api_key`

## [0.8.11] — 2026-02-21

### Added

- Obsidian-git setup instructions shown in `/obsidian` hub when GitHub is connected (all 4 languages)

### Fixed

- OpenRouter default model changed to `deepseek/deepseek-r1-0528:free`
- AI provider errors now log response body (up to 300 chars) for easier diagnosis

## [0.8.10] — 2026-02-21

### Fixed

- `context` variable in `voice.py` shadowed the Telegram `context` parameter when storing recent transcriptions, causing
  `AttributeError: 'list' object has no attribute 'bot'`; renamed to `recent_context`
- OpenRouter default model `deepseek/deepseek-chat-v3-0324:free` returned 404; changed to `deepseek/deepseek-r1:free`
- Groq moved to end of LLM fallback chain; fallback order is now openrouter → gemini → groq
- `get_github_file` logged ERROR on 404 (e.g. `vocabulary.json` not yet created); now logs DEBUG for 404, ERROR for
  other failures

## [0.8.9] — 2026-02-21

### Fixed

- Wit.ai usage limit check was incorrectly comparing combined requests across all language apps against a single limit;
  each Wit.ai app (token) now has its own counter

### Changed

- Default LLM provider switched from Gemini to OpenRouter (`deepseek/deepseek-chat-v3-0324:free`) — accessible from
  Russia
- Wit.ai usage tracking is now per-language (per-token): each language app tracked independently with its own counter
  and alerts
- `auto_cleanup` setting now only controls Telegram/WhatsApp reply — Obsidian always receives cleaned text regardless
- `classify_note` now returns `(category, keywords)` tuple via JSON response instead of plain category string
- Cleanup transcript accepts `vocabulary` and `context` optional parameters

### Added

- Admin panel: LLM provider switcher (Categ / GPT) via inline keyboard — changes take effect immediately without
  restart; stored in MongoDB (`BotConfig`)
- Dual-save in Obsidian: notes contain cleaned text + `<!-- original ... -->` HTML comment with raw transcription when
  texts differ
- Recent transcription context: last 3 notes from the same chat (TTL 2h, keep last 5) are passed to the cleanup LLM for
  better context
- `vocabulary.json` in GitHub repo: auto-built from categorization keywords, merged per category (max 50 per category)
- Cleanup prompt now uses domain vocabulary and recent context for better transcription quality

## [0.8.0] — 2025

### Added

- Monetization: credits system, token billing, Telegram Stars payments
- VIP and Tester user tiers
- Monthly usage stats and admin alerts (Wit.ai 80%/95% thresholds, revenue milestones)
- Rate limiter for LLM providers with retry logic and fallback chain

### Changed

- Switched to Groq as transcription provider alongside Wit.ai (provider selection per chat)
- Added OpenRouter and Gemini as LLM provider options with fallback chains

## [0.7.0] — 2025

### Added

- WhatsApp integration via Meta Cloud API
- WhatsApp ↔ Telegram account linking
- End-to-end tests (TROPHY style: real DB with mongomock, mocks only at external boundaries)

## [0.6.0] — 2025

### Added

- GitHub OAuth integration
- Obsidian integration: save transcriptions to GitHub repo as markdown notes with frontmatter
- Auto-categorization: move notes to category folders in Obsidian repo
- AI-powered transcript cleanup (GPT)
- Multi-language support: Russian, English, Spanish, German (separate Wit.ai apps per language)

## [0.5.0] — 2025

### Added

- Groq transcription provider
- Admin panel with system stats
- Start menu and language selection flow

## [0.4.0] — 2024

### Added

- Telegram groups support
- Per-chat settings (language, command prefix)
- MongoDB for persistent storage

## [0.1.0] — 2024

### Added

- Initial Telegram bot with Wit.ai voice transcription
- Docker Compose setup
- GitHub Actions CI
