# Evlampiy Notes Bot

[![CI](https://github.com/yastcher/evlampiy/actions/workflows/deploy.yml/badge.svg)](https://github.com/yastcher/evlampiy/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](https://github.com/yastcher/evlampiy)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](../LICENSE)

[English](../README.md) | [Русский](README.ru.md) | [Español](README.es.md) | Deutsch

Sprache-zu-Text Bot für Telegram und WhatsApp mit mehrsprachiger Unterstützung.

**Ausprobieren:** https://t.me/evlampiy_notes_bot

## Funktionen

- **Sprachtranskription** — Wandelt Sprachnachrichten in Text um mit [Wit.ai](https://wit.ai/)
- **Groq Whisper Fallback** — Automatischer Wechsel zu [Groq](https://groq.com/) Whisper wenn das monatliche
  Wit.ai-Limit erreicht ist
- **Kreditsystem** — Monetarisierung über Telegram Stars mit Kreditguthaben pro Benutzer
- **Multiplattform** — Funktioniert mit Telegram und WhatsApp
- **Mehrsprachig** — Unterstützt Englisch, Deutsch, Russisch, Spanisch
- **Chat-Einstellungen** — Jeder Benutzer/Gruppe kann individuelle Spracheinstellungen haben
- **GPT-Integration** — GPT-Befehle per Sprache auslösen (sag "evlampiy" + deine Frage)
- **Obsidian-Integration** — Automatische Speicherung von Sprachtranskriptionen in Obsidian über GitHub (OAuth Device
  Flow)
- **Auto-Kategorisierung** — Automatische Klassifizierung von Notizen mit Claude Haiku

## Architektur

```
src/
├── transcription/       # Domain-Schicht (plattformunabhängig)
│   ├── service.py       # Transkriptionslogik
│   ├── wit_client.py    # Wit.ai-Clients
│   └── groq_client.py   # Groq Whisper-Client
├── telegram/            # Telegram-Adapter
│   ├── bot.py
│   ├── handlers.py
│   ├── voice.py
│   └── payments.py      # Telegram Stars Zahlungs-Handler
├── whatsapp/            # WhatsApp-Adapter
│   ├── client.py
│   └── handlers.py
├── credits.py           # Kreditsystem & Nutzungsstatistiken
├── wit_tracking.py      # Monatliche Wit.ai-Nutzungsverfolgung
├── const.py             # Gemeinsame Konstanten
├── github_oauth.py      # GitHub OAuth Device Flow
├── github_api.py        # GitHub-API-Operationen
├── obsidian.py          # Obsidian-Integration
├── categorization.py    # Auto-Kategorisierung mit Claude
└── main.py              # Einstiegspunkt
```

## Voraussetzungen

- Python 3.12+
- MongoDB
- FFmpeg (für Audioverarbeitung)
- [Wit.ai](https://wit.ai/) API-Tokens
- Telegram Bot-Token von [@BotFather](https://t.me/BotFather)
- (Optional) WhatsApp Business API-Zugangsdaten
- (Optional) GitHub OAuth App Client-ID (für Obsidian-Integration)
- (Optional) [Groq](https://groq.com/) API-Schlüssel (für Whisper-Fallback-Transkription)
- (Optional) [Anthropic](https://anthropic.com/) API-Schlüssel (für Auto-Kategorisierung)

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

# Optional: GitHub OAuth (für Obsidian-Integration)
GITHUB_CLIENT_ID=deine_github_oauth_app_client_id

# Optional: Monetarisierung
GROQ_API_KEY=dein_groq_api_schluessel
VIP_USER_IDS=123456,789012
ADMIN_USER_IDS=123456789
INITIAL_CREDITS=3
WIT_FREE_MONTHLY_LIMIT=500
```

Für WhatsApp-Einrichtungsanleitung, siehe [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md).

## Bot-Befehle

| Befehl                  | Beschreibung                                     |
|-------------------------|--------------------------------------------------|
| `/start`                | Hilfe und aktuelle Einstellungen anzeigen        |
| `/choose_your_language` | Erkennungssprache festlegen                      |
| `/enter_your_command`   | GPT-Triggerwort festlegen                        |
| `/buy`                  | Kredite mit Telegram Stars kaufen                |
| `/balance`              | Aktuelles Kreditguthaben anzeigen                |
| `/mystats`              | Ihre Nutzungsstatistiken anzeigen                |
| `/connect_github`       | GitHub-Konto verbinden (OAuth Device Flow)       |
| `/toggle_obsidian`      | Obsidian-Synchronisierung ein-/ausschalten       |
| `/toggle_categorize`    | Auto-Kategorisierung ein-/ausschalten            |
| `/categorize`           | Alle Notizen im income-Ordner kategorisieren     |
| `/disconnect_github`    | GitHub trennen und Synchronisierung deaktivieren |

Für Admin-Befehle siehe [ADMIN.md](ADMIN.md).

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
- [x] Obsidian-Integration über GitHub OAuth
- [x] Monetarisierung (Telegram Stars, Kreditsystem, Groq Whisper)
- [x] Nachrichtenklassifizierung nach Themen (Auto-Kategorisierung mit Claude Haiku)

## Lizenz

Proprietär. Alle Rechte vorbehalten. Siehe [LICENSE](../LICENSE).
