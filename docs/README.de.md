# Evlampiy Notes Bot

[![CI](https://github.com/yastcher/evlampiy/actions/workflows/deploy.yml/badge.svg)](https://github.com/yastcher/evlampiy/actions)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen.svg)](https://github.com/yastcher/evlampiy)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](../LICENSE)

[English](../README.md) | [Русский](README.ru.md) | [Español](README.es.md) | Deutsch

Sprache-zu-Text Bot für Telegram und WhatsApp mit mehrsprachiger Unterstützung.

**Ausprobieren:** https://t.me/evlampiy_notes_bot

## Funktionen

### Kern
- **Sprachtranskription** — Sofortige Umwandlung von Sprachnachrichten in Text
- **Multiplattform** — Telegram und WhatsApp
- **Mehrsprachig** — Englisch, Deutsch, Russisch, Spanisch
- **Chat-Einstellungen** — Individuelle Sprache und Trigger für jeden Chat
- **KI-Textbereinigung** — Optionale LLM-gestützte Bereinigung von Transkriptionen (entfernt Füllwörter, korrigiert Zeichensetzung). Wenn die Bereinigung deaktiviert ist, bleibt die Telegram-Antwort roh, Obsidian-Notizen werden jedoch stets bereinigt.

### Transkriptionsanbieter
- **Wit.ai** — Standardanbieter mit monatlicher Limitüberwachung
- **Groq Whisper** — Fallback bei Erreichen des Wit.ai-Limits; zahlende Nutzer können manuell über `/settings` wählen

### Monetarisierung
- **Token-System** — 10 kostenlose Tokens/Monat + kaufbare Pakete (1 Token = 20 Sek. Audio)
- **Telegram Stars** — Native Zahlungsintegration mit 4 Paketstufen
- **Benutzerstufen** — Free, Paid, VIP, Tester, Admin, Blocked

### Obsidian-Integration
- **GitHub-Synchronisierung** — Automatisches Speichern von Transkriptionen in Ihrem Vault über GitHub API
- **OAuth Device Flow** — Sichere Authentifizierung ohne Token-Offenlegung
- **Auto-Kategorisierung** — KI-gestützte Notizklassifizierung (Google Gemini, Anthropic Claude, OpenAI)
- **Duales Speichern** — Notizen enthalten bereinigten Text; die rohe Transkription wird in einem HTML-Kommentar aufbewahrt
- **vocabulary.json** — Automatisch aufgebaute Stichwortliste je Kategorie; verbessert die Korrektur von Transkriptionsfehlern
- **Bereinigungskontext** — Neueste Transkriptionen aus demselben Chat werden dem LLM zur präziseren Bereinigung übergeben

### Kontoverknüpfung
- **Telegram ↔ WhatsApp** — Konten mit Einmalcodes verknüpfen
- **Rate Limiting** — Schutz gegen Brute-Force-Angriffe

### Administration
- **Admin-Panel** — `/admin` Hub mit Inline-Buttons in Telegram
- **Benutzerverwaltung** — VIP- und Tester-Benutzer hinzufügen/entfernen, sperren/entsperren, Tokens aufladen über Telegram
- **Nutzungsstatistiken** — Monatliche Transkriptionen, Einnahmen, Kosten
- **Gesundheitsüberwachung** — Wit.ai/Groq-Nutzungsalarme

## Voraussetzungen

- Python 3.13+
- MongoDB
- FFmpeg (für Audioverarbeitung)
- [Wit.ai](https://wit.ai/) API-Tokens
- Telegram Bot-Token von [@BotFather](https://t.me/BotFather)
- (Optional) WhatsApp Business API-Zugangsdaten
- (Optional) GitHub OAuth App Client-ID (für Obsidian-Integration)
- (Optional) [Groq](https://groq.com/) API-Schlüssel (für Whisper-Fallback-Transkription)
- (Optional) API-Schlüssel eines KI-Anbieters — [Google Gemini](https://ai.google.dev/), [Anthropic](https://anthropic.com/) oder [OpenAI](https://openai.com/) (für Auto-Kategorisierung und GPT-Befehle)

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
GPT_MODEL=gpt-4o-mini

# Optional: WhatsApp-Integration (siehe WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=dein_whatsapp_token
WHATSAPP_PHONE_ID=deine_phone_id
WHATSAPP_VERIFY_TOKEN=dein_verify_token

# Optional: GitHub OAuth (für Obsidian-Integration)
# Für manuelle Token-Einrichtung, siehe docs/GITHUB_TOKEN_SETUP.md
GITHUB_CLIENT_ID=deine_github_oauth_app_client_id

# Optional: Monetarisierung
GROQ_API_KEY=dein_groq_api_schluessel
VIP_USER_IDS=123456,789012   # Env-Fallback; Verwaltung über /admin in Telegram
ADMIN_USER_IDS=123456789
FREE_MONTHLY_TOKENS=10
WIT_FREE_MONTHLY_LIMIT=500
```

Für WhatsApp-Einrichtungsanleitung, siehe [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md).

## Bot-Befehle

| Befehl      | Beschreibung                             |
|-------------|------------------------------------------|
| `/start`    | Hilfe und aktuelle Einstellungen         |
| `/settings` | Sprache, GPT-Befehl und Anbieter         |
| `/obsidian` | Notizen-Synchronisierung mit GitHub      |
| `/account`  | Guthaben, Tokens und WhatsApp-Verknüpfung |

Für Admin-Befehle siehe [ADMIN.md](ADMIN.md).

## Entwicklung

### Ansatz

- **DDD** — Domain-Driven Design mit klaren Modulgrenzen (`transcription/`, `telegram/`, `whatsapp/`)
- **TDD** — Erst Tests, dann Implementierung
- **Trophy Testing** — Integrationstests mit echter DB (mongomock), Mocks nur an externen Grenzen

### Befehle

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

## Lizenz

Proprietär. Alle Rechte vorbehalten. Siehe [LICENSE](../LICENSE).
