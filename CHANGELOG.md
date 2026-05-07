## [0.9.0] — 2026-04-13

### Added

- script for bump

### Fixed

- WhatsApp webhook wiring: `whatsapp/app.py` called `wa.setup_fastapi(app)` which does not exist in
  pywa and would raise `AttributeError` at runtime if WhatsApp credentials were configured. Reworked
  initialization: `init_whatsapp_client(server)` now creates the `WhatsApp` client with `server=app`
  in the constructor (the documented pywa pattern), so webhook routes are registered correctly.
  Replaced `global _wa_client` with a `_WhatsAppClientHolder` class per project convention
- MongoDB image pinned to `mongo:8.0.3` in both `docker-compose.yml` and
  `.devcontainer/docker-compose.dev.yml` to prevent regression: versions 8.0.5..8.0.20 and 8.2.x crash
  with SIGSEGV ~30s after startup on hosts with kernel 6.x + glibc 2.39+. Verified working: 8.0.3,
  8.0.4. Re-test before bumping past 8.0.4.
- Selftest LLM-cleanup check sent the raw transcription text directly to `cleanup_text` (low-level
  LLM call) without the cleanup system prompt. The model treated the input as a chat message and
  replied conversationally ("Отлично! Поздравляю..."), making the check a false-positive. Fixed by
  prepending `CLEANUP_PROMPT_BASE` (the same prompt used by `cleanup_transcript` in production) to
  the sample before the LLM call.

### Changed

- Replaced mypy with ty (Astral) as the type checker. Config moved to `[tool.ty]` in pyproject.toml;
  `uv run ty check src` is the new command (CI, docs, CLAUDE.md updated).
  Tech debt: 6 type errors silenced with `# ty: ignore[invalid-argument-type, missing-argument]`
  (pywa decorator stubs, PTB `ConversationHandler` generic variance, Beanie/Motor db type).
  Find via `rg "# ty: ignore" src/`
- Resolved all `unresolved-attribute` ignores by tightening narrowing:
  `query.message`/`callback_query.message` now use `isinstance(..., Message)`; `effective_user`
  re-checked after `is_bot_sender`; `message.text` defaulted via `or ""` in WhatsApp link command.
  Added `mock_callback_query.message = MagicMock(spec=Message)` in fixtures so handler tests still pass
- FastAPI `/health` tests reworked as integration (real `create_fastapi_app`, WhatsApp disabled via
  `fastapi_app_no_whatsapp` fixture) — no longer depend on local `.env` WhatsApp credentials
- **Migrated Telegram framework: python-telegram-bot v22 → aiogram v3.27.** Full rewrite of
  `src/telegram/*`, `src/main.py`, `src/alerts.py`, `src/selftest.py`, `src/gpt_commands.py`.
    - Lifecycle: `ApplicationBuilder` → `Bot + Dispatcher + Router` with `await dp.start_polling(bot)`.
    - Conversation FSM: `ConversationHandler` → `aiogram.fsm.state.StatesGroup` (`GptCommandStates.waiting`).
    - Bot-sender guard: `TypeHandler(group=-1) + ApplicationHandlerStop` → `BotSenderRejectMiddleware`
      on `dp.update.outer_middleware`.
    - Filters: `filters.VOICE | filters.AUDIO`, `filters.SUCCESSFUL_PAYMENT`, `filters.TEXT & ~filters.COMMAND`
      → magic-filter `F.voice | F.audio`, `F.successful_payment`, `F.text & ~F.text.startswith("/")`.
    - Callback handlers: aiogram-native `(callback: CallbackQuery, bot: Bot)` signatures; PTB
      `Update`/`Context` thread is gone.
    - Voice download: `voice.get_file().download_as_bytearray()` → `bot.download(voice, destination=buf)`.
    - Selftest `bot.send_voice(voice=bytes)` → `BufferedInputFile(bytes, filename=...)`.
    - `chat_params.py` accepts `Message | CallbackQuery` directly; `is_user_admin(event, bot)` takes
      `Bot` instead of PTB `Context`.
    - Test fixtures rewritten as aiogram-shape mocks; ~190 tests updated.
    - Removed three `# ty: ignore[invalid-argument-type]` PTB-ConversationHandler suppressions.
    - Net effect: `uv run ty check src` shows 6 → 3 ignores (only Beanie/Motor + 2 pywa stubs remain).
- aiohttp constraint pinned to `>=3.13.4` to address CVE-2026-3451x cluster (transitive via aiogram).
- Architecture isolation: extracted `build_stats_text` from `src/telegram/handlers.py` to a new
  `src/services/stats_service.py` (framework-agnostic). Breaks the cyclic-ish dependency
  `src/telegram/admin.py → src/telegram/handlers.py` — admin now imports the service directly.
  Tests `TestBuildStatsWitStatus*` moved to `tests/services/test_stats_service.py`. First step of
  `.claude/plans/architecture-isolation.md`.
- Architecture isolation: added `src/services/voice_pipeline.py::process_voice` —
  framework-agnostic transcription → cleanup → Obsidian → categorize pipeline. Both
  `src/telegram/voice.py::from_voice_to_text` and
  `src/whatsapp/handlers.py::handle_voice_message` became thin adapters that
  download audio + call the service; ~50 lines of duplicated cleanup/Obsidian/categorize logic
  consolidated. Telegram-specific concerns (credits, alerts, gpt-command formatting,
  provider selection) stay in the adapter. Service-level smoke tests added in
  `tests/services/test_voice_pipeline.py`. Existing voice tests updated via fixture rewiring
  (`voice_external_mocks` / `whatsapp_voice_external_mocks` patches now target the service).
- Architecture isolation: turned `src/telegram/handlers.py` into a `src/telegram/handlers/`
  package and grouped all handler modules under it. Result:
  `src/telegram/handlers/{common,account,admin,obsidian,payments,settings,voice}.py`.
  `common.py` keeps the cross-cutting handlers from the old `handlers.py`
  (`/start`, GPT-command FSM, `/stats`, `hub_callback_router`); the others are the
  former `*_handlers.py` files renamed to short domain names. `src/telegram/setup.py`
  now imports the submodules with `as`-aliases that match the legacy variable names
  (`handlers`, `account_handlers`, etc.) so the routing table is unchanged.
  No `*` re-exports in `__init__.py` — every caller uses an explicit
  `from src.telegram.handlers.<domain> import …`. Test imports updated by sed (~30
  files); `docs/test_docs.py::TestArchitectureFreshness._parse_tree_files` was
  hardened to support arbitrary tree nesting (the old parser only tracked one level).
- Architecture isolation: removed all PTB-compat aliases from `tests/fixtures.py`
  (`msg.effective_user`/`effective_chat` aliasing, `msg.message = msg` self-reference,
  `mock_context.bot = mock_context` self-reference, and the
  `mock_callback_query.edit_message_text` PTB-shorthand). Mocks now have a
  faithful aiogram shape: tests access `mock_private_update.from_user` /
  `mock_private_update.chat`, set `mock_private_update.successful_payment` directly,
  call `bot.X` as `mock_context.X`, and use `mock_callback_query.message.edit_text`.
  Test files moved into a `tests/telegram/` package (`test_user_flow.py`,
  `test_admin.py`, `test_handlers_extended.py`, `test_payments.py`,
  `test_account_linking.py`, `test_bot.py`, `test_gpt_commands.py`,
  `test_bot_sender_guard.py`, `test_selftest.py`) so handler / adapter tests are
  visually grouped next to the new `tests/services/` package. Infra tests
  (`test_ai_*`, `test_mongo`, `test_transcription`, `test_categorization`,
  `test_github_*`, etc.) stay at `tests/` root.
- Architecture isolation: added `src/services/payments_service.py` —
  framework-agnostic Telegram-Stars payment crediting. Owns `CREDIT_PACKAGES` (business
  data: `name` / `stars` / `tokens`), `package_payload(idx)` / `tokens_for_payload`
  helpers, and `award_tokens(user_id, payload, total_amount) -> AwardResult` which
  resolves payload → tokens, calls `add_credits` + `increment_payment_stats`, and
  returns the new balance. `src/telegram/payments.py::handle_successful_payment` is now
  a thin adapter (~20 lines): calls `award_tokens`, then triggers admin alerts and
  sends confirmation via the aiogram Bot. The keyboard's `callback_data` (`buy_pkg_N`)
  is generated by index in the adapter — only the payload contract
  (`buy_tokens_N`) crosses the service boundary, via the `package_payload` helper.
  Service-level tests added in `tests/services/test_payments_service.py`. Two redundant
  handler tests (`TestSuccessfulPayment::{test_tokens_added_on_package_payment,
  test_legacy_payment_fallback}`) removed from `tests/test_payments.py`; the smoke
  `TestPaymentFlow` integration test stays.
- Architecture isolation: added three more domain services that hold the actual business
  rules previously inlined in handlers. `src/services/notes_service.py` —
  `toggle_save_to_obsidian` / `toggle_auto_categorize` / `categorize_all_for_chat (has_repo, count)`.
  `src/services/settings_service.py` — `toggle_auto_cleanup`, `set_chat_provider_choice` (maps
  UI token → persisted provider + confirmation key). `src/services/admin_service.py` — pure
  `parse_user_id` / `parse_credits_amount` validators plus `assign_role` / `revoke_role` /
  `block_user` / `unblock_user` / `change_credits` mongo wrappers (centralizes the audit logging
  for blocks). Telegram handlers in `obsidian_handlers.py` / `settings_handlers.py` / `admin.py`
  shrunk to thin adapters: i18n + keyboards + auth checks remain there, all toggles/validations
  delegate to services. Pure-logic tests added in `tests/services/test_admin_service.py`,
  `test_settings_service.py`, `test_notes_service.py`. Existing handler tests rewired one
  patch (`src.telegram.obsidian_handlers.categorize_all_income` →
  `src.services.notes_service.categorize_all_income`).
- Unified asyncio loop: replaced `threading.Thread(target=run_fastapi_server)` in `src/main.py` with
  `asyncio.TaskGroup` running `run_bot()` and `serve_fastapi()` (uvicorn `Server.serve()`) in the same
  loop. Eliminates threading/asyncio mix — graceful shutdown, exception propagation, and shared
  state without locks. `src/whatsapp/app.py::run_fastapi_server` (sync) replaced by
  `serve_fastapi` (async). Side-effect of moving pywa into the main loop: switched
  `from pywa import WhatsApp` → `from pywa_async import WhatsApp` in `src/whatsapp/{client,handlers}.py`
  and converted `asyncio.to_thread(wa.send_message, ...)` / `wa.get_media_url(...)` to direct
  `await wa.send_message(...)` / `await wa.get_media_url(...)`. Without this the async pywa callbacks
  raise `ValueError: Async callbacks ... are not supported in the sync version of pywa`.

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
