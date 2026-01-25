# Evlampiy Notes Bot

[![CI](https://github.com/YastYa/evlampiy_notes_tgbot/actions/workflows/deploy.yml/badge.svg)](https://github.com/YastYa/evlampiy_notes_tgbot/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](https://github.com/YastYa/evlampiy_notes_tgbot)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

[Русский](README.ru.md) | [Español](README.es.md) | Deutsch | [English](../README.md)

Sprache-zu-Text Bot für Telegram und WhatsApp mit mehrsprachiger Unterstützung.

**Ausprobieren:** https://t.me/evlampiy_notes_bot

## Funktionen

- **Sprachtranskription** — Wandelt Sprachnachrichten in Text um mit [Wit.ai](https://wit.ai/)
- **Multiplattform** — Funktioniert mit Telegram und WhatsApp
- **Mehrsprachig** — Unterstützt Englisch, Deutsch, Russisch, Spanisch
- **Chat-Einstellungen** — Jeder Benutzer/Gruppe kann individuelle Spracheinstellungen haben
- **GPT-Integration** — GPT-Befehle per Sprache auslösen (sag "evlampiy" + deine Frage)
- **Obsidian-Export** — Notizen in deinem Obsidian-Vault über GitHub speichern

## Architektur

```
src/
├── transcription/       # Domain-Schicht (plattformunabhängig)
│   ├── service.py       # Transkriptionslogik
│   └── wit_client.py    # Wit.ai-Clients
├── telegram/            # Telegram-Adapter
│   ├── bot.py
│   ├── handlers.py
│   └── voice.py
├── whatsapp/            # WhatsApp-Adapter
│   ├── client.py
│   └── handlers.py
└── main.py              # Einstiegspunkt
```

## Voraussetzungen

- Python 3.12+
- MongoDB
- FFmpeg (für Audioverarbeitung)
- [Wit.ai](https://wit.ai/) API-Tokens
- Telegram Bot-Token von [@BotFather](https://t.me/BotFather)
- (Optional) WhatsApp Business API-Zugangsdaten

## Schnellstart

```bash
# Klonen
git clone https://github.com/yastcher/evlampiy.git
cd evlampiy

# Abhängigkeiten installieren
pip install uv
uv sync

# Konfigurieren
cp .env.example .env
# Bearbeite .env mit deinen Tokens

# Starten
uv run python -m src.main
```

## Konfiguration

Erstelle die `.env` Datei:

```env
TELEGRAM_BOT_TOKEN=dein_bot_token
MONGO_URI=mongodb://localhost:27017/

# Wit.ai Tokens (erhältlich auf https://wit.ai/)
WIT_EN_TOKEN=dein_englisch_token
WIT_RU_TOKEN=dein_russisch_token
WIT_ES_TOKEN=dein_spanisch_token
WIT_DE_TOKEN=dein_deutsch_token

# Optional: GPT-Integration
GPT_TOKEN=dein_openai_token

# Optional: WhatsApp-Integration (siehe WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=dein_whatsapp_token
WHATSAPP_PHONE_ID=deine_phone_id
WHATSAPP_VERIFY_TOKEN=dein_verify_token
```

Für WhatsApp-Einrichtungsanleitung, siehe [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md).

## Bot-Befehle

| Befehl                  | Beschreibung                              |
|-------------------------|-------------------------------------------|
| `/start`                | Hilfe und aktuelle Einstellungen anzeigen |
| `/choose_your_language` | Erkennungssprache festlegen               |
| `/enter_your_command`   | GPT-Triggerwort festlegen                 |

## Entwicklung

```bash
# Dev-Abhängigkeiten installieren
uv sync --group dev

# Tests ausführen
uv run pytest

# Linter ausführen
uv run ruff check

# Mit Coverage ausführen
uv run pytest --cov=src --cov-fail-under=85
```

## Deployment

Siehe [DEPLOY.md](../DEPLOY.md) für Docker-Deployment-Anweisungen.

## Roadmap

- [x] Sprache-zu-Text Transkription
- [x] Mehrsprachige Unterstützung (EN, RU, ES, DE)
- [ ] GPT-Integration
- [x] CI/CD mit GitHub Actions
- [x] WhatsApp-Integration
- [ ] Obsidian-Export Verbesserungen
- [ ] Nachrichtenklassifizierung nach Themen

## Lizenz

[GPL-3.0](../LICENSE)
