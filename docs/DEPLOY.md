# Deployment Guide

[Русский](#развёртывание) | [English](#english)

---

## English

### Installation

```bash
git clone https://github.com/yastcher/evlampiy.git
cd evlampiy
pip install uv
uv sync
```

### Configuration

Create `.env` file:

```env
# Required: Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
MONGO_URI=mongodb://localhost:27017/

# Required: Wit.ai (voice recognition)
WIT_RU_TOKEN=your_wit_ru_token
WIT_EN_TOKEN=your_wit_en_token
WIT_ES_TOKEN=your_wit_es_token
WIT_DE_TOKEN=your_wit_de_token

# Optional: GPT integration
GPT_TOKEN=your_openai_token
GPT_MODEL=gpt-4o-mini

# Optional: WhatsApp integration (see docs/WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
WHATSAPP_APP_ID=your_app_id
WHATSAPP_APP_SECRET=your_app_secret

# Optional: GitHub OAuth (for Obsidian integration)
GITHUB_CLIENT_ID=your_github_oauth_app_client_id

# Optional: Monetization
GROQ_API_KEY=your_groq_api_key
VIP_USER_IDS=123456,789012
ADMIN_USER_IDS=123456789
FREE_MONTHLY_TOKENS=10
WIT_FREE_MONTHLY_LIMIT=500

# Optional: AI provider for categorization and GPT (deepseek / groq / gemini / openrouter / anthropic)
CATEGORIZATION_PROVIDER=deepseek
GPT_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### Local Run

```bash
uv run python -m src.main
```

### Docker

#### Build and Run

```bash
docker build -t evlampiy_notes:latest .
docker compose up -d
```

#### Docker Compose

The `docker-compose.yml` includes:
- MongoDB database
- Bot service with auto-restart

For WhatsApp integration, port 8000 is exposed for webhook callbacks.

#### Telegram blocked on the host

If `api.telegram.org` is unreachable from the host (e.g. a Russian VPS), deploy the Cloudflare
Worker in `cloudflare/telegram-proxy/` and set `TELEGRAM_API_BASE` to its URL. Empty = official
endpoint.

#### LLM providers blocked on the host

If the LLM provider APIs (Groq / OpenRouter / Gemini / Anthropic / OpenAI) are geo-blocked from the
host, deploy the Cloudflare Worker in `cloudflare/llm-proxy/` and set `LLM_API_BASE` to its URL.
Empty = providers are called directly. DeepSeek and Qwen are reached directly and not proxied.

### Server deploy (CI/CD)

Releases roll out from the `release` branch via `.github/workflows/deploy.yml`: lint + type check +
tests, then the image is built, tagged `:<commit-sha>` (immutable rollback handle) and `:latest`,
and pushed to **GHCR** (`ghcr.io/yastcher/evlampiy_notes`). The deploy step copies
`docker-compose.yml` over SSH, pins `EVLAMPIY_IMAGE` + `IMAGE_TAG` in the server's `.env`, pulls the
image and recreates only the bot container — MongoDB is never restarted. If `/health` does not
answer within 30s, the job fails and dumps the container logs.

The registry needs no extra secret: the image lives in this repo's GHCR namespace, and both push and
pull are authorized with the built-in `GITHUB_TOKEN` (job permission `packages: write`).

#### GitHub secrets

| Name | Description |
|---|---|
| `SSH_PRIVATE_KEY` | base64 ssh key (`cat ~/.ssh/id_rsa \| base64 -w0`); the user must be in the `docker` group |
| `SERVER_IP` | server IP / hostname |
| `SERVER_USER` | ssh user — unprivileged, not `root` (e.g. `yast`) |
| `DEPLOY_DIR` | optional, path relative to `~`; defaults to `evlampiy` |

#### Server prep (once)

```bash
# Docker + compose plugin, then let the deploy user talk to the daemon
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER" && newgrp docker

mkdir -p ~/evlampiy && cd ~/evlampiy
# Put the real .env here (see Configuration above) — CI does not deploy it.
```

The deploy dir holds `mongo_data/`, the bind mount backing MongoDB — **it is the database**. Back it
up (`docker compose exec -T mongodb mongodump --archive --gzip > dump.gz`) before moving or deleting
the directory.

#### Rollback

`IMAGE_TAG` in the server's `.env` is the release commit SHA, so any previous release can be
restored without CI:

```bash
cd ~/evlampiy
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<previous-sha>/' .env
docker compose up -d
```

### WhatsApp Webhook Setup

If using WhatsApp integration:

1. **Port forwarding**: Ensure port 8000 is accessible from the internet
2. **HTTPS**: WhatsApp requires HTTPS. Use a reverse proxy (nginx, Caddy) with SSL
3. **Webhook URL**: Configure in Meta Developer Console as `https://your-domain.com/`

Example nginx configuration:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Health Check

The bot always exposes a liveness endpoint (served even when WhatsApp is not configured):

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

`docker-compose.yml` wires a container healthcheck to it (status shows in `docker ps`). Plain
Compose reports health but does not restart unhealthy containers — pair it with an orchestrator
or an autoheal sidecar if you want automatic restart on failure.

### Development

```bash
# Install dev dependencies
uv sync --group dev

# Run linter
uv run ruff check

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-fail-under=85
```

### Logs

```bash
# Docker logs
docker compose logs -f evlampiy_bot

# Filter by level
docker compose logs evlampiy_bot 2>&1 | grep ERROR
```

---

## Развёртывание

### Установка

```bash
git clone https://github.com/yastcher/evlampiy.git
cd evlampiy
pip install uv
uv sync
```

### Конфигурация

Создайте файл `.env`:

```env
# Обязательно: Telegram
TELEGRAM_BOT_TOKEN=ваш_токен_бота
MONGO_URI=mongodb://localhost:27017/

# Обязательно: Wit.ai (распознавание голоса)
WIT_RU_TOKEN=ваш_wit_ru_токен
WIT_EN_TOKEN=ваш_wit_en_токен
WIT_ES_TOKEN=ваш_wit_es_токен
WIT_DE_TOKEN=ваш_wit_de_токен

# Опционально: интеграция с GPT
GPT_TOKEN=ваш_openai_токен
GPT_MODEL=gpt-4o-mini

# Опционально: интеграция с WhatsApp (см. docs/WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=ваш_whatsapp_токен
WHATSAPP_PHONE_ID=ваш_phone_id
WHATSAPP_VERIFY_TOKEN=ваш_verify_токен
WHATSAPP_APP_ID=ваш_app_id
WHATSAPP_APP_SECRET=ваш_app_secret

# Опционально: GitHub OAuth (для интеграции с Obsidian)
GITHUB_CLIENT_ID=ваш_github_oauth_app_client_id

# Опционально: Монетизация
GROQ_API_KEY=ваш_groq_api_ключ
VIP_USER_IDS=123456,789012
ADMIN_USER_IDS=123456789
FREE_MONTHLY_TOKENS=10
WIT_FREE_MONTHLY_LIMIT=500

# Опционально: AI-провайдер для категоризации и GPT (deepseek / groq / gemini / openrouter / anthropic)
CATEGORIZATION_PROVIDER=deepseek
GPT_PROVIDER=deepseek
DEEPSEEK_API_KEY=ваш_deepseek_api_ключ
GEMINI_API_KEY=ваш_gemini_api_ключ
```

### Локальный запуск

```bash
uv run python -m src.main
```

### Docker

#### Сборка и запуск

```bash
docker build -t evlampiy_notes:latest .
docker compose up -d
```

#### Docker Compose

`docker-compose.yml` включает:
- База данных MongoDB
- Сервис бота с авто-перезапуском

Для интеграции с WhatsApp порт 8000 открыт для webhook-колбэков.

#### Telegram заблокирован на хосте

Если `api.telegram.org` недоступен с хоста (например, российский VPS), задеплойте Cloudflare
Worker из `cloudflare/telegram-proxy/` и укажите `TELEGRAM_API_BASE` с его URL. Пусто = официальный
endpoint.

#### LLM-провайдеры заблокированы на хосте

Если API LLM-провайдеров (Groq / OpenRouter / Gemini / Anthropic / OpenAI) гео-блокнуты с хоста,
задеплойте Cloudflare Worker из `cloudflare/llm-proxy/` и укажите `LLM_API_BASE` с его URL. Пусто =
прямые вызовы. DeepSeek и Qwen ходят напрямую и не проксируются.

### Деплой на сервер (CI/CD)

Релизы катятся из ветки `release` через `.github/workflows/deploy.yml`: линтер + тайпчекер + тесты,
затем сборка образа, теги `:<commit-sha>` (неизменяемый handle для отката) и `:latest`, push в
**GHCR** (`ghcr.io/yastcher/evlampiy_notes`). Шаг деплоя копирует по SSH `docker-compose.yml`, пинит
`EVLAMPIY_IMAGE` + `IMAGE_TAG` в серверном `.env`, тянет образ и пересоздаёт только контейнер бота —
MongoDB не перезапускается. Если `/health` не отвечает 30 секунд, job падает и печатает логи
контейнера.

Реестр не требует дополнительных секретов: образ лежит в GHCR-неймспейсе этого же репозитория, push
и pull авторизуются встроенным `GITHUB_TOKEN` (job-permission `packages: write`).

#### GitHub secrets

| Имя | Описание |
|---|---|
| `SSH_PRIVATE_KEY` | base64 ssh-ключ (`cat ~/.ssh/id_rsa \| base64 -w0`); пользователь должен быть в группе `docker` |
| `SERVER_IP` | IP / hostname сервера |
| `SERVER_USER` | пользователь для ssh — непривилегированный, не `root` (например `yast`) |
| `DEPLOY_DIR` | опционально, путь относительно `~`; по умолчанию `evlampiy` |

#### Подготовка сервера (один раз)

```bash
# Docker + compose-plugin, затем доступ деплой-юзера к демону
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER" && newgrp docker

mkdir -p ~/evlampiy && cd ~/evlampiy
# Положите сюда настоящий .env (см. «Конфигурация» выше) — CI его не деплоит.
```

В деплой-директории лежит `mongo_data/` — bind-mount MongoDB, **то есть сама база**. Перед переносом
или удалением директории снимите бэкап:
`docker compose exec -T mongodb mongodump --archive --gzip > dump.gz`.

#### Откат

`IMAGE_TAG` в серверном `.env` — это SHA коммита релиза, поэтому любой предыдущий релиз
восстанавливается без CI:

```bash
cd ~/evlampiy
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<предыдущий-sha>/' .env
docker compose up -d
```

### Настройка Webhook для WhatsApp

При использовании WhatsApp:

1. **Проброс портов**: Порт 8000 должен быть доступен из интернета
2. **HTTPS**: WhatsApp требует HTTPS. Используйте reverse proxy (nginx, Caddy) с SSL
3. **URL Webhook**: Настройте в Meta Developer Console как `https://ваш-домен.com/`

Пример конфигурации nginx:

```nginx
server {
    listen 443 ssl;
    server_name ваш-домен.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Проверка работоспособности

Бот предоставляет endpoint для проверки:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Разработка

```bash
# Установка dev-зависимостей
uv sync --group dev

# Запуск линтера
uv run ruff check

# Запуск тестов
uv run pytest

# Запуск с покрытием
uv run pytest --cov=src --cov-fail-under=85
```

### Логи

```bash
# Логи Docker
docker compose logs -f evlampiy_bot

# Фильтр по уровню
docker compose logs evlampiy_bot 2>&1 | grep ERROR
```
