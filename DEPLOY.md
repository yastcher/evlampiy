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

# Optional: Monetization
GROQ_API_KEY=your_groq_api_key
VIP_USER_IDS=123456,789012
INITIAL_CREDITS=3
WIT_FREE_MONTHLY_LIMIT=500
```

### Local Run

```bash
uv run python -m src.main
```

### Docker

#### Build and Run

```bash
docker build -t evlampiy_notes_tgbot:latest .
docker compose up -d
```

#### Docker Compose

The `docker-compose.yml` includes:
- MongoDB database
- Bot service with auto-restart

For WhatsApp integration, port 8000 is exposed for webhook callbacks.

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

The bot exposes a health endpoint:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

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

# Опционально: Монетизация
GROQ_API_KEY=ваш_groq_api_ключ
VIP_USER_IDS=123456,789012
INITIAL_CREDITS=3
WIT_FREE_MONTHLY_LIMIT=500
```

### Локальный запуск

```bash
uv run python -m src.main
```

### Docker

#### Сборка и запуск

```bash
docker build -t evlampiy_notes_tgbot:latest .
docker compose up -d
```

#### Docker Compose

`docker-compose.yml` включает:
- База данных MongoDB
- Сервис бота с авто-перезапуском

Для интеграции с WhatsApp порт 8000 открыт для webhook-колбэков.

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
