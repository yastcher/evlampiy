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
