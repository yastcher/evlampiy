# Evlampiy Notes Bot

[![CI](https://github.com/yastcher/evlampiy/actions/workflows/deploy.yml/badge.svg)](https://github.com/yastcher/evlampiy/actions)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen.svg)](https://github.com/yastcher/evlampiy)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](../LICENSE)

[English](../README.md) | [Русский](README.ru.md) | Español | [Deutsch](README.de.md)

Bot de voz a texto para Telegram y WhatsApp con soporte multilingüe.

**Pruébalo:** https://t.me/evlampiy_notes_bot

## Características

### Principal
- **Transcripción de voz** — Conversión instantánea de mensajes de voz a texto
- **Multiplataforma** — Telegram y WhatsApp
- **Multilingüe** — Inglés, alemán, ruso, español
- **Configuración por chat** — Idioma y trigger individual para cada chat

### Proveedores de transcripción
- **Wit.ai** — Proveedor predeterminado con seguimiento del límite mensual
- **Groq Whisper** — Respaldo cuando se alcanza el límite de Wit.ai; usuarios de pago pueden elegir manualmente en `/settings`

### Monetización
- **Sistema de tokens** — 10 tokens gratis/mes + paquetes comprables (1 token = 20 seg de audio)
- **Telegram Stars** — Integración de pagos nativa con 4 niveles de paquetes
- **Niveles de usuario** — Free, Paid, VIP, Tester, Admin, Blocked

### Integración con Obsidian
- **Sincronización GitHub** — Guardado automático de transcripciones en tu vault vía GitHub API
- **OAuth Device Flow** — Autenticación segura sin exponer tokens
- **Auto-categorización** — Clasificación de notas con IA usando Claude Haiku

### Vinculación de cuentas
- **Telegram ↔ WhatsApp** — Vincula cuentas con códigos de un solo uso
- **Rate limiting** — Protección contra ataques de fuerza bruta

### Administración
- **Panel de administración** — Hub `/admin` con botones inline en Telegram
- **Gestión de usuarios** — Añadir/eliminar usuarios VIP y testers, bloquear/desbloquear, recargar tokens vía Telegram
- **Estadísticas de uso** — Transcripciones, ingresos, costos mensuales
- **Monitoreo de salud** — Alertas de uso de Wit.ai/Groq

## Requisitos

- Python 3.13+
- MongoDB
- FFmpeg (para procesamiento de audio)
- Tokens API de [Wit.ai](https://wit.ai/)
- Token de bot Telegram de [@BotFather](https://t.me/BotFather)
- (Opcional) Credenciales de WhatsApp Business API
- (Opcional) GitHub OAuth App client ID (para integración con Obsidian)
- (Opcional) [Groq](https://groq.com/) API key (para transcripción de respaldo Whisper)
- (Opcional) [Anthropic](https://anthropic.com/) API key (para auto-categorización)

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
GPT_MODEL=gpt-4o-mini

# Opcional: integración WhatsApp (ver WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=tu_token_whatsapp
WHATSAPP_PHONE_ID=tu_phone_id
WHATSAPP_VERIFY_TOKEN=tu_verify_token

# Opcional: GitHub OAuth (para integración con Obsidian)
# Para configuración manual del token, ver docs/GITHUB_TOKEN_SETUP.md
GITHUB_CLIENT_ID=tu_github_oauth_app_client_id

# Opcional: Monetización
GROQ_API_KEY=tu_groq_api_key
VIP_USER_IDS=123456,789012   # env fallback; gestionar vía /admin en Telegram
ADMIN_USER_IDS=123456789
FREE_MONTHLY_TOKENS=10
WIT_FREE_MONTHLY_LIMIT=500
```

Para instrucciones de configuración de WhatsApp, consulta [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md).

## Comandos del Bot

| Comando     | Descripción                              |
|-------------|------------------------------------------|
| `/start`    | Mostrar ayuda y configuración actual     |
| `/settings` | Idioma, comando GPT y proveedor           |
| `/obsidian` | Sincronización de notas con GitHub       |
| `/account`  | Saldo, tokens y vinculación WhatsApp     |

Para comandos de administrador, ver [ADMIN.md](ADMIN.md).

## Desarrollo

### Enfoque

- **DDD** — Diseño guiado por dominio con límites claros de módulos (`transcription/`, `telegram/`, `whatsapp/`)
- **TDD** — Primero tests, luego implementación
- **Trophy Testing** — Tests de integración con BD real (mongomock), mocks solo en límites externos

### Comandos

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

## Licencia

Propietaria. Todos los derechos reservados. Ver [LICENSE](../LICENSE).
