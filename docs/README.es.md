# Evlampiy Notes Bot

[![CI](https://github.com/yastcher/evlampiy/actions/workflows/deploy.yml/badge.svg)](https://github.com/yastcher/evlampiy/actions)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/yastcher/evlampiy)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](../LICENSE)

[English](../README.md) | [Русский](README.ru.md) | Español | [Deutsch](README.de.md)

Bot de voz a texto para Telegram y WhatsApp con soporte multilingüe.

**Pruébalo:** https://t.me/evlampiy_notes_bot

## Características

- **Transcripción de voz** — Convierte mensajes de voz a texto usando [Wit.ai](https://wit.ai/)
- **Respaldo Groq Whisper** — Cambio automático a [Groq](https://groq.com/) Whisper cuando se alcanza el límite mensual de Wit.ai
- **Sistema de créditos** — Monetización mediante Telegram Stars con saldo de créditos por usuario
- **Multiplataforma** — Funciona con Telegram y WhatsApp
- **Multilingüe** — Soporta inglés, alemán, ruso, español
- **Configuración por chat** — Cada usuario/grupo puede tener preferencias de idioma individuales
- **Integración con GPT** — Activa comandos GPT por voz (di "evlampiy" + tu pregunta)
- **Integración con Obsidian** — Guardado automático de transcripciones de voz en Obsidian vía GitHub (OAuth Device Flow)

## Arquitectura

```
src/
├── transcription/       # Capa de dominio (agnóstica de plataforma)
│   ├── service.py       # Lógica de transcripción
│   ├── wit_client.py    # Clientes Wit.ai
│   └── groq_client.py   # Cliente Groq Whisper
├── telegram/            # Adaptador Telegram
│   ├── bot.py
│   ├── handlers.py
│   ├── voice.py
│   └── payments.py      # Manejadores de pagos Telegram Stars
├── whatsapp/            # Adaptador WhatsApp
│   ├── client.py
│   └── handlers.py
├── credits.py           # Sistema de créditos y estadísticas
├── wit_tracking.py      # Seguimiento de uso mensual de Wit.ai
├── const.py             # Constantes compartidas
├── github_oauth.py      # GitHub OAuth Device Flow
├── github_api.py        # Operaciones de GitHub API
├── obsidian.py          # Integración con Obsidian
└── main.py              # Punto de entrada
```

## Requisitos

- Python 3.12+
- MongoDB
- FFmpeg (para procesamiento de audio)
- Tokens API de [Wit.ai](https://wit.ai/)
- Token de bot Telegram de [@BotFather](https://t.me/BotFather)
- (Opcional) Credenciales de WhatsApp Business API
- (Opcional) GitHub OAuth App client ID (para integración con Obsidian)
- (Opcional) [Groq](https://groq.com/) API key (para transcripción de respaldo Whisper)

## Inicio Rápido

```bash
# Clonar
git clone https://github.com/yastcher/evlampiy.git
cd evlampiy

# Instalar dependencias
pip install uv
uv sync

# Configurar
cp .env.example .env
# Edita .env con tus tokens

# Ejecutar
uv run python -m src.main
```

## Configuración

Crea el archivo `.env`:

```env
TELEGRAM_BOT_TOKEN=tu_token_de_bot
MONGO_URI=mongodb://localhost:27017/

# Tokens Wit.ai (obtener en https://wit.ai/)
WIT_EN_TOKEN=tu_token_ingles
WIT_RU_TOKEN=tu_token_ruso
WIT_ES_TOKEN=tu_token_espanol
WIT_DE_TOKEN=tu_token_aleman

# Opcional: integración GPT
GPT_TOKEN=tu_token_openai

# Opcional: integración WhatsApp (ver WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=tu_token_whatsapp
WHATSAPP_PHONE_ID=tu_phone_id
WHATSAPP_VERIFY_TOKEN=tu_verify_token

# Opcional: GitHub OAuth (para integración con Obsidian)
GITHUB_CLIENT_ID=tu_github_oauth_app_client_id

# Opcional: Monetización
GROQ_API_KEY=tu_groq_api_key
VIP_USER_IDS=123456,789012
INITIAL_CREDITS=3
WIT_FREE_MONTHLY_LIMIT=500
```

Para instrucciones de configuración de WhatsApp, consulta [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md).

## Comandos del Bot

| Comando                 | Descripción                                      |
|-------------------------|--------------------------------------------------|
| `/start`                | Mostrar ayuda y configuración actual             |
| `/choose_your_language` | Establecer idioma de reconocimiento              |
| `/enter_your_command`   | Establecer palabra activadora de GPT             |
| `/buy`                  | Comprar créditos con Telegram Stars              |
| `/balance`              | Mostrar saldo actual de créditos                 |
| `/connect_github`       | Conectar cuenta de GitHub (OAuth Device Flow)    |
| `/toggle_obsidian`      | Activar/desactivar sincronización con Obsidian   |
| `/disconnect_github`    | Desconectar GitHub y desactivar sincronización   |

## Desarrollo

```bash
# Instalar dependencias de desarrollo
uv sync --group dev

# Ejecutar tests
uv run pytest

# Ejecutar linter
uv run ruff check

# Ejecutar con cobertura
uv run pytest --cov=src --cov-fail-under=85
```

## Despliegue

Consulta [DEPLOY.md](../DEPLOY.md) para instrucciones de despliegue con Docker.

## Roadmap

- [x] Transcripción de voz a texto
- [x] Soporte multilingüe (EN, RU, ES, DE)
- [ ] Integración con GPT
- [x] CI/CD con GitHub Actions
- [x] Integración con WhatsApp
- [x] Integración con Obsidian vía GitHub OAuth
- [x] Monetización (Telegram Stars, sistema de créditos, Groq Whisper)
- [ ] Clasificación de mensajes por temas

## Licencia

Propietaria. Todos los derechos reservados. Ver [LICENSE](../LICENSE).
