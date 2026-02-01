# Evlampiy Notes Bot

[![CI](https://github.com/yastcher/evlampiy/actions/workflows/deploy.yml/badge.svg)](https://github.com/yastcher/evlampiy/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](https://github.com/yastcher/evlampiy)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

English | [Русский](docs/README.ru.md) | [Español](docs/README.es.md) | [Deutsch](docs/README.de.md)

Voice-to-text bot for Telegram and WhatsApp with multi-language support.

**Try it:** https://t.me/evlampiy_notes_bot

## Features

- **Voice transcription** — Convert voice messages to text using [Wit.ai](https://wit.ai/)
- **Groq Whisper fallback** — Automatic fallback to [Groq](https://groq.com/) Whisper when Wit.ai monthly limit is
  reached
- **Credit system** — Monetization via Telegram Stars with per-user credit balance
- **Multi-platform** — Works with Telegram and WhatsApp
- **Multi-language** — Supports English, German, Russian, Spanish
- **Per-chat settings** — Each user/group can have individual language preferences
- **GPT integration** — Trigger GPT commands via voice (say "evlampiy" + your question)
- **Obsidian integration** — Auto-save voice transcriptions to Obsidian vault via GitHub (OAuth Device Flow)
- **Auto-categorization** — Automatically classify notes into categories using Claude Haiku

## Architecture

```
src/
├── transcription/       # Domain layer (platform-agnostic)
│   ├── service.py       # Core transcription logic
│   ├── wit_client.py    # Wit.ai clients
│   └── groq_client.py   # Groq Whisper client
├── telegram/            # Telegram adapter
│   ├── bot.py
│   ├── handlers.py
│   ├── voice.py
│   ├── payments.py      # Telegram Stars payment handlers
│   └── chat_params.py   # Chat identification helpers
├── whatsapp/            # WhatsApp adapter
│   ├── client.py
│   └── handlers.py
├── config.py            # Application settings
├── const.py             # Shared constants
├── credits.py           # Credit system & usage stats
├── dto.py               # Data transfer objects
├── mongo.py             # MongoDB operations
├── wit_tracking.py      # Wit.ai monthly usage tracking
├── gpt_commands.py      # GPT command handler
├── localization.py      # Multi-language translations
├── alerts.py            # Admin alert service
├── github_oauth.py      # GitHub OAuth Device Flow
├── github_api.py        # GitHub API operations
├── obsidian.py          # Obsidian vault integration
├── categorization.py    # Note auto-categorization with Claude
└── main.py              # Application entry point
```

## Requirements

- Python 3.12+
- MongoDB
- FFmpeg (for audio processing)
- [Wit.ai](https://wit.ai/) API tokens
- Telegram Bot token from [@BotFather](https://t.me/BotFather)
- (Optional) WhatsApp Business API credentials
- (Optional) GitHub OAuth App client ID (for Obsidian integration)
- (Optional) [Groq](https://groq.com/) API key (for Whisper fallback)
- (Optional) [Anthropic](https://anthropic.com/) API key (for auto-categorization)

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
VIP_USER_IDS=123456,789012
ADMIN_USER_IDS=123456789
INITIAL_CREDITS=3
WIT_FREE_MONTHLY_LIMIT=500

# Optional: Auto-categorization (requires Obsidian integration)
ANTHROPIC_API_KEY=your_anthropic_api_key
```

For WhatsApp setup instructions, see [docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md).

## Bot Commands

| Command                 | Description                                |
|-------------------------|--------------------------------------------|
| `/start`                | Show help and current settings             |
| `/choose_your_language` | Set voice recognition language             |
| `/enter_your_command`   | Set custom GPT trigger word                |
| `/buy`                  | Buy credits with Telegram Stars            |
| `/balance`              | Show current credit balance                |
| `/mystats`              | Show your personal usage statistics        |
| `/connect_github`       | Connect GitHub account (OAuth Device Flow) |
| `/toggle_obsidian`      | Enable/disable Obsidian sync               |
| `/toggle_categorize`    | Enable/disable auto-categorization         |
| `/categorize`           | Categorize all notes in income folder      |
| `/disconnect_github`    | Disconnect GitHub and disable sync         |
| `/link_whatsapp`        | Link your WhatsApp account                 |
| `/unlink_whatsapp`      | Unlink your WhatsApp account               |

For admin commands, see [docs/ADMIN.md](docs/ADMIN.md).

## Development

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

## Roadmap

- [x] Voice-to-text transcription
- [x] Multi-language support (EN, RU, ES, DE)
- [ ] GPT command integration
- [x] CI/CD with GitHub Actions
- [x] WhatsApp integration
- [x] Obsidian integration via GitHub OAuth
- [x] Monetization (Telegram Stars, credit system, Groq Whisper fallback)
- [x] Message classification by topics (auto-categorization with Claude Haiku)
- [ ] ChatMemberUpdated handler for cleanup

## License

Proprietary. All rights reserved. See [LICENSE](LICENSE).
