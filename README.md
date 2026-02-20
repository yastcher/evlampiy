# Evlampiy Notes Bot

[![CI](https://github.com/yastcher/evlampiy/actions/workflows/deploy.yml/badge.svg)](https://github.com/yastcher/evlampiy/actions)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen.svg)](https://github.com/yastcher/evlampiy)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

English | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | [Deutsch](docs/README.de.md)

Voice-to-text bot for Telegram and WhatsApp with multi-language support.

**Try it:** https://t.me/evlampiy_notes_bot

## Features

### Core
- **Voice transcription** — Convert voice messages to text instantly
- **Multi-platform** — Telegram and WhatsApp support
- **Multi-language** — English, German, Russian, Spanish
- **Per-chat settings** — Individual language and trigger preferences
- **AI text cleanup** — Optional LLM-powered cleanup of transcriptions (removes filler words, fixes punctuation). When `/settings` cleanup is OFF, reply text stays raw but Obsidian notes are still cleaned silently.

### Transcription Providers
- **Wit.ai** — Default provider with monthly limit tracking
- **Groq Whisper** — Fallback when Wit.ai limit reached; paid users can select manually via `/settings`

### Monetization
- **Token system** — 10 free tokens/month + purchasable packages (1 token = 20 sec audio)
- **Telegram Stars** — Native payment integration with 4 package tiers
- **User tiers** — Free, Paid, VIP, Tester, Admin, Blocked

### Obsidian Integration
- **GitHub sync** — Auto-save transcriptions to your vault via GitHub API
- **OAuth Device Flow** — Secure authentication without exposing tokens
- **Auto-categorization** — AI-powered note classification (Google Gemini, Anthropic Claude, OpenAI)
- **Dual-save** — Notes contain cleaned text; raw transcription preserved in an HTML comment for reference
- **vocabulary.json** — Auto-built per-category keyword list; improves transcription error correction over time
- **Cleanup context** — Recent transcriptions from the same chat are passed to the cleanup LLM for better accuracy

### Account Linking
- **Telegram ↔ WhatsApp** — Link accounts with one-time codes
- **Rate limiting** — Protection against brute-force attacks

### Administration
- **Admin panel** — `/admin` hub with inline buttons in Telegram
- **User management** — Add/remove VIP and tester users, block/unblock users, top up tokens via Telegram commands
- **Usage stats** — Monthly transcriptions, revenue, costs
- **Health monitoring** — Wit.ai/Groq usage alerts

## Requirements

- Python 3.13+
- MongoDB
- FFmpeg (for audio processing)
- [Wit.ai](https://wit.ai/) API tokens
- Telegram Bot token from [@BotFather](https://t.me/BotFather)
- (Optional) WhatsApp Business API credentials
- (Optional) GitHub OAuth App client ID (for Obsidian integration)
- (Optional) [Groq](https://groq.com/) API key (for Whisper fallback)
- (Optional) AI provider API key — [Google Gemini](https://ai.google.dev/), [Anthropic](https://anthropic.com/), or [OpenAI](https://openai.com/) (for auto-categorization and GPT commands)

## Quick Start

```bash
# Clone
git clone https://github.com/yastcher/evlampiy.git
cd evlampiy

# Install dependencies
pip install uv
uv sync

# Configure
cp .env.example .env
# Edit .env with your tokens

# Run
uv run python -m src.main
```

## Configuration

Create `.env` file:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
MONGO_URI=mongodb://localhost:27017/

# Wit.ai tokens (get from https://wit.ai/)
WIT_EN_TOKEN=your_english_token
WIT_RU_TOKEN=your_russian_token
WIT_ES_TOKEN=your_spanish_token
WIT_DE_TOKEN=your_german_token

# Optional: GPT integration
GPT_TOKEN=your_openai_token
GPT_MODEL=gpt-4o-mini

# Optional: WhatsApp integration (see docs/WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token

# Optional: GitHub OAuth (for Obsidian integration)
# For manual token setup, see docs/GITHUB_TOKEN_SETUP.md
GITHUB_CLIENT_ID=your_github_oauth_app_client_id

# Optional: Monetization
GROQ_API_KEY=your_groq_api_key
VIP_USER_IDS=123456,789012   # env fallback; manage via /admin in Telegram
ADMIN_USER_IDS=123456789
FREE_MONTHLY_TOKENS=10
WIT_FREE_MONTHLY_LIMIT=500

# Optional: AI provider for categorization and GPT (groq / gemini / openrouter / anthropic / openai)
# groq is recommended — free tier, fast, no rate-limit issues
# Fallback chain (auto): primary → groq → openrouter → gemini
CATEGORIZATION_PROVIDER=groq
GPT_PROVIDER=groq
GEMINI_API_KEY=your_gemini_api_key  # optional fallback
```

For WhatsApp setup instructions, see [docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md).

## Bot Commands

| Command     | Description                              |
|-------------|------------------------------------------|
| `/start`    | Show help and current settings           |
| `/settings` | Language, GPT command & provider settings |
| `/obsidian` | Notes sync to GitHub (Obsidian vault)    |
| `/account`  | Balance, tokens & WhatsApp linking       |

For admin commands, see [docs/ADMIN.md](docs/ADMIN.md).

## Development

### Approach

- **DDD** — Domain-driven design with clear module boundaries (`transcription/`, `telegram/`, `whatsapp/`)
- **TDD** — Tests first, implementation second
- **Trophy Testing** — Integration tests with real DB (mongomock), mocks only at external boundaries

### Commands

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run linter
uv run ruff check

# Run with coverage
uv run pytest --cov=src --cov-fail-under=85
```

## Deployment

See [DEPLOY.md](DEPLOY.md) for Docker deployment instructions.

## License

Proprietary. All rights reserved. See [LICENSE](LICENSE).
