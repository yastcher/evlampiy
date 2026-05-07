# Architecture

## Overview

Evlampiy Notes Bot is an async Python application that transcribes voice messages from Telegram and WhatsApp into text. It uses FastAPI for WhatsApp webhooks, aiogram for Telegram polling, MongoDB (via Beanie ODM) for persistence, and multiple AI providers with automatic fallback chains. The codebase follows domain-driven design with modular boundaries.

## Directory Structure

```
src/
├── telegram/               # Telegram bot (aiogram)
│   ├── handlers/           - Per-domain handler modules (PR6 of architecture-isolation)
│   │   ├── common.py       - Core handlers (/start, stats, hub router, GPT command conversation)
│   │   ├── settings.py     - Settings hub (/settings, language, provider, cleanup toggle)
│   │   ├── obsidian.py     - Obsidian hub (/obsidian, GitHub OAuth, categorization)
│   │   ├── account.py      - Account hub (/account, mystats, WhatsApp linking)
│   │   ├── admin.py        - Admin panel and user management (/admin)
│   │   ├── voice.py        - Voice message transcription handler
│   │   └── payments.py     - Telegram Stars payment integration
│   ├── bot.py              - Message sending utilities
│   ├── chat_params.py      - Chat ID extraction and admin checks
│   └── setup.py            - aiogram dispatcher + router builder, handler registration
├── whatsapp/               # WhatsApp Cloud API (pywa)
│   ├── handlers.py         - Voice message and account link handler
│   ├── client.py           - WhatsApp API client wrapper
│   └── app.py              - FastAPI webhook server
├── transcription/          # Speech-to-text service
│   ├── service.py          - Provider-agnostic transcription API
│   ├── wit_client.py       - Wit.ai integration (chunked audio)
│   └── groq_client.py      - Groq Whisper integration
├── services/               # Use-case layer (framework-agnostic, no aiogram/pywa)
│   ├── admin_service.py    - Role assignment, block/unblock, credits, user-id validation
│   ├── notes_service.py    - Toggle Obsidian sync / auto-categorize, run categorize_all
│   ├── payments_service.py - Token packages + award_tokens on successful Stars payment
│   ├── settings_service.py - Toggle auto-cleanup, persist transcription provider choice
│   ├── stats_service.py    - Admin /stats text builder
│   └── voice_pipeline.py   - Transcription → cleanup → Obsidian → categorize pipeline
├── ai_client.py            - Multi-provider LLM client with token bucket rate limiter
├── ai_chat.py              - Messages-based chat completion with tool calling support
├── tools.py                - Tool definitions and implementations for GPT tool calling
├── tool_calling.py         - Tool-calling conversation loop (execute → re-send)
├── account_linking.py      - Telegram ↔ WhatsApp linking with brute-force protection
├── categorization.py       - AI-powered note categorization into Obsidian folders
├── credits.py              - Token system, user tiers, credit deduction
├── wit_tracking.py         - Per-language monthly Wit.ai usage tracking
├── alerts.py               - Admin alerts (payments, usage thresholds, revenue)
├── mongo.py                - Beanie ODM initialization and common queries
├── config.py               - Pydantic-settings configuration from .env
├── const.py                - Constants (provider names, roles, limits)
├── types.py                - Domain type aliases (UserId, ChatId, Language, MonthKey)
├── dto.py                  - MongoDB document models (Beanie Documents)
├── localization.py         - Multi-language UI strings (en, ru, es, de)
├── prompts.py              - LLM prompt templates
├── transcript_cleanup.py   - AI-powered transcription text cleanup
├── github_api.py           - GitHub API client for Obsidian vault operations
├── github_oauth.py         - GitHub OAuth Device Flow authentication
├── obsidian.py             - Save transcriptions as markdown to GitHub repo
├── gpt_commands.py         - GPT chat command handler with tool calling
├── main.py                 - Application entry point (Telegram + FastAPI startup)
└── selftest.py             - Health check and self-test endpoints
```

```
tests/
├── fixtures.py             - All shared test fixtures (no fixtures in test files)
├── conftest.py             - Pytest configuration and plugin imports
├── test_architecture.py    - Domain isolation and import style rules (pytestarch)
├── test_api_contracts.py   - Handler registration, signatures, menu consistency
├── test_docs.py            - Link validation, ARCHITECTURE.md freshness, CHANGELOG format
├── services/               - Use-case service tests (no aiogram/pywa mocks)
│   └── test_*_service.py, test_voice_pipeline.py
├── telegram/               - Adapter-level handler tests (aiogram-shape mocks)
│   └── test_user_flow.py, test_admin.py, test_payments.py, ...
└── test_*.py               - Integration and unit tests for shared/infra code
```

## Data Flow

### Voice Message Processing

```
User sends voice message (Telegram or WhatsApp)
         │
         ▼
┌─────────────────────────────────────────────┐
│ 1. RECEIVE & VALIDATE                       │
│    telegram/voice.py or whatsapp/handlers.py│
│    Download audio, check user not blocked   │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│ 2. SELECT PROVIDER                          │
│    Check user tier + Wit.ai availability    │
│    Free → Wit.ai only                       │
│    Paid/VIP/Admin → Wit.ai, Groq fallback   │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│ 3. TRANSCRIBE                               │
│    transcription/service.py                 │
│    Wit.ai: chunk at 20s, combine results    │
│    Groq: send entire audio file             │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│ 4. DEDUCT CREDITS                           │
│    credits.py: ceil(duration / 20) tokens   │
│    Free pool first, then purchased          │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│ 5. OPTIONAL: AI CLEANUP                     │
│    transcript_cleanup.py via ai_client.py   │
│    Context: last 3 transcriptions (TTL 2h)  │
│    + per-category vocabulary                │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│ 6. OPTIONAL: SAVE TO OBSIDIAN               │
│    obsidian.py → github_api.py              │
│    Dual-save: clean + raw in HTML comment   │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│ 7. OPTIONAL: AUTO-CATEGORIZE                │
│    categorization.py via ai_client.py       │
│    Returns (category, keywords)             │
│    Moves note to folder, updates vocabulary │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│ 8. RESPOND                                  │
│    Send transcription back to user          │
│    Check & send admin alerts if needed      │
└─────────────────────────────────────────────┘
```

### LLM Request Flow

```
ai_client.py receives request with preferred provider
         │
         ▼
    Rate limiter (token bucket) checks capacity
         │
    ┌────┴────┐
    │ OK      │ Rate limited
    ▼         ▼
  Send    Retry with backoff (2s, 4s, 8s — max 3 retries)
  request      │
    │     ┌────┴────┐
    │     │ OK      │ Still limited
    │     ▼         ▼
    │   Send     Next provider in fallback chain
    │   request  deepseek → openrouter → gemini → groq
    │                │
    │           All exhausted → RateLimitError
    ▼
  Return response
```

## External Services

| Service | Purpose | Module | Free Tier Limit |
|---------|---------|--------|-----------------|
| Wit.ai | Primary speech-to-text | `transcription/wit_client.py` | 500 req/month per language |
| Groq Whisper | Fallback speech-to-text | `transcription/groq_client.py` | 7,200 sec/day |
| DeepSeek | Primary LLM (cleanup, categorize) | `ai_client.py` | 60 RPM |
| OpenRouter | LLM fallback | `ai_client.py` | 10 RPM |
| Google Gemini | LLM fallback | `ai_client.py` | 15 RPM |
| Groq LLM | LLM fallback | `ai_client.py` | 30 RPM |
| GitHub API | Obsidian vault sync | `github_api.py` | 5,000 req/hour |
| Telegram Bot API | Messaging, file downloads | `telegram/` | Polling, no hard limit |
| WhatsApp Cloud API | Messaging, media | `whatsapp/` | Business API limits |
| MongoDB | Persistence | `mongo.py`, `dto.py` | Self-hosted |

## Rate Limits & Quotas

### Account Linking

Brute-force protection for Telegram ↔ WhatsApp linking.

| Parameter | Value | Source |
|-----------|-------|--------|
| Code length | 6 digits | `account_linking.py:LINK_CODE_LENGTH` |
| Code TTL | 5 minutes | `account_linking.py:LINK_CODE_TTL_SECONDS` |
| Max attempts | 5 per phone | `account_linking.py:LINK_MAX_ATTEMPTS` |
| Lockout duration | 5 minutes | `account_linking.py:LINK_LOCKOUT_SECONDS` |

### AI Providers (Token Bucket)

Each provider has an independent token bucket with per-minute capacity.

| Provider | RPM | Source |
|----------|-----|--------|
| DeepSeek | 60 | `ai_client.py:_PROVIDER_LIMITS` |
| Qwen | 60 | `ai_client.py:_PROVIDER_LIMITS` |
| Groq | 30 | `ai_client.py:_PROVIDER_LIMITS` |
| Gemini | 15 | `ai_client.py:_PROVIDER_LIMITS` |
| OpenRouter | 10 | `ai_client.py:_PROVIDER_LIMITS` |

Retry strategy: 3 attempts with exponential backoff (2s, 4s, 8s). If all retries fail, the request falls through to the next provider in the chain.

Fallback chains (configurable at runtime via admin panel):
- **Categorization:** deepseek → openrouter → gemini → groq
- **GPT commands:** deepseek → openrouter → gemini → groq

### Wit.ai Usage

| Parameter | Value | Source |
|-----------|-------|--------|
| Monthly limit | 500 req per language | `config.py:WIT_FREE_MONTHLY_LIMIT` |
| Languages tracked | en, ru, es, de (independent counters) | `wit_tracking.py` |
| Warning alert | 80% usage | `alerts.py` |
| Critical alert | 95% usage | `alerts.py` |
| On exhaustion | Fallback to Groq Whisper | `transcription/service.py` |

### User Tokens

| Parameter | Value | Source |
|-----------|-------|--------|
| Token cost | 1 token = 20 seconds of audio | `const.py:SECONDS_PER_TOKEN` |
| Free tier | 10 tokens/month | `config.py:FREE_MONTHLY_TOKENS` |
| Deduction order | Free pool first, then purchased | `credits.py` |
| Purchase method | Telegram Stars (4 package tiers) | `telegram/payments.py` |

### User Tiers

| Tier | Transcription | Provider | Tokens |
|------|--------------|----------|--------|
| Admin | Unlimited | Groq priority | N/A |
| VIP | Unlimited | Groq priority | N/A |
| Tester | Unlimited | Wit.ai + Groq fallback | Admin top-up |
| Paid | Token-based | Wit.ai + Groq fallback | Purchased via Stars |
| Free | 10/month | Wit.ai only | Purchasable |
| Blocked | Denied | N/A | N/A |

## Engineering Decisions

### DDD with Modular Structure

The codebase is organized by domain (`telegram/`, `whatsapp/`, `transcription/`) rather than by technical layer. Each platform handler is self-contained, while shared services (`credits`, `ai_client`, `categorization`) live at the `src/` root level. This keeps related logic together and makes it easy to add new platforms.

### Trophy Testing

Tests use real MongoDB (via mongomock-motor) and real application logic. Mocks are applied only at external I/O boundaries: HTTP APIs (Wit.ai, Groq, GitHub, LLM providers), Telegram Bot API, and WhatsApp Cloud API. This catches integration bugs that unit-test-heavy approaches miss. All fixtures live in `tests/fixtures.py` — test files have zero fixture definitions.

In addition to integration tests, three contract test suites guard structural invariants:

- **`test_architecture.py`** — pytestarch rules enforce domain isolation (telegram ↔ whatsapp never import each other, transcription is channel-independent) and stdlib import style (`import datetime`, not `from datetime import ...`).
- **`test_api_contracts.py`** — every command in `COMMAND_HANDLERS` is async with `(update, context)` signature; all `BOT_COMMANDS` / `ADMIN_COMMANDS` menu entries map to registered handlers; all callback query handlers exist; `/health` endpoint returns expected schema.
- **`test_docs.py`** — all internal markdown links resolve to existing files; every `.py` file in `src/` is listed in `ARCHITECTURE.md` (and vice versa); all READMEs have a Documentation table; CHANGELOG subsection names are from the allowed set.

### Token Bucket Rate Limiting

Each LLM provider has a per-minute token bucket (`ai_client.py`). When a bucket is empty, the request retries with exponential backoff. If still rate-limited after 3 retries, it falls through to the next provider in the fallback chain. This provides resilience against free-tier rate limits without manual intervention.

### Multi-Provider Fallback Chains

Two independent chains exist: one for categorization, one for GPT commands. Both default to `deepseek → openrouter → gemini → groq`. Chains can be switched at runtime via the admin panel (stored in MongoDB `BotConfig`) without restart.

### Brute-Force Protection for Account Linking

Telegram ↔ WhatsApp linking uses time-limited 6-digit codes with per-phone attempt tracking. After 5 failed attempts, the phone is locked out for 5 minutes. Codes expire after 5 minutes regardless.

### Tiered Access Model

Free users get Wit.ai only (no Groq fallback, no provider choice). This keeps costs predictable for the free tier. Paid users unlock Groq fallback and manual provider selection via `/settings`.

### Async Throughout

The entire stack is async: FastAPI for WhatsApp webhooks, aiogram for Telegram polling, httpx for outbound HTTP, and Beanie (async Motor) for MongoDB. The entry point (`main.py`) runs Telegram polling in the main thread and FastAPI in a daemon thread.

### Context-Aware Cleanup

The AI cleanup step receives the last 3 transcriptions from the same chat (TTL 2 hours) as context, plus per-category vocabulary from `vocabulary.json`. This allows the LLM to resolve ambiguous words using surrounding topic context and domain-specific terminology.
