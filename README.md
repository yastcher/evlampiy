# Evlampiy Notes Bot

[![CI](https://github.com/YastYa/evlampiy_notes_tgbot/actions/workflows/deploy.yml/badge.svg)](https://github.com/YastYa/evlampiy_notes_tgbot/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](https://github.com/YastYa/evlampiy_notes_tgbot)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

[Русский](docs/README.ru.md) | [Español](docs/README.es.md) | [Deutsch](docs/README.de.md) | English

Voice-to-text bot for Telegram and WhatsApp with multi-language support.

**Try it:** https://t.me/evlampiy_notes_bot

## Features

- **Voice transcription** — Convert voice messages to text using [Wit.ai](https://wit.ai/)
- **Multi-platform** — Works with Telegram and WhatsApp
- **Multi-language** — Supports English, German, Russian, Spanish
- **Per-chat settings** — Each user/group can have individual language preferences
- **GPT integration** — Trigger GPT commands via voice (say "evlampiy" + your question)
- **Obsidian export** — Save notes to your Obsidian vault via GitHub

## Architecture

```
src/
├── transcription/       # Domain layer (platform-agnostic)
│   ├── service.py       # Core transcription logic
│   └── wit_client.py    # Wit.ai clients
├── telegram/            # Telegram adapter
│   ├── bot.py
│   ├── handlers.py
│   └── voice.py
├── whatsapp/            # WhatsApp adapter
│   ├── client.py
│   └── handlers.py
└── main.py              # Application entry point
```

## Requirements

- Python 3.12+
- MongoDB
- FFmpeg (for audio processing)
- [Wit.ai](https://wit.ai/) API tokens
- Telegram Bot token from [@BotFather](https://t.me/BotFather)
- (Optional) WhatsApp Business API credentials

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

# Optional: WhatsApp integration (see docs/WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
```

For WhatsApp setup instructions, see [docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md).

## Bot Commands

| Command                 | Description                    |
|-------------------------|--------------------------------|
| `/start`                | Show help and current settings |
| `/choose_your_language` | Set voice recognition language |
| `/enter_your_command`   | Set custom GPT trigger word    |

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
- [ ] Obsidian export improvements
- [ ] Message classification by topics
- [ ] ChatMemberUpdated handler for cleanup

## License

[GPL-3.0](LICENSE)
