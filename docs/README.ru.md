# Evlampiy Notes Bot

[![CI](https://github.com/yastcher/evlampiy/actions/workflows/deploy.yml/badge.svg)](https://github.com/yastcher/evlampiy/actions)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A590%25-brightgreen.svg)](https://github.com/yastcher/evlampiy)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](../LICENSE)

[English](../README.md) | Русский | [Español](README.es.md) | [Deutsch](README.de.md)

Telegram и WhatsApp бот для транскрипции голосовых сообщений с поддержкой нескольких языков.

**Попробовать:** https://t.me/evlampiy_notes_bot

## Возможности

### Основное
- **Транскрипция голоса** — Мгновенное преобразование голосовых сообщений в текст
- **Мультиплатформенность** — Telegram и WhatsApp
- **Мультиязычность** — Английский, немецкий, русский, испанский
- **Настройки по чатам** — Индивидуальный язык и триггер для каждого чата

### Провайдеры транскрипции
- **Wit.ai** — Провайдер по умолчанию с отслеживанием месячного лимита
- **Groq Whisper** — Фоллбэк при исчерпании лимита Wit.ai; платные пользователи могут выбрать вручную через `/settings`

### Монетизация
- **Система токенов** — 10 бесплатных токенов/месяц + покупные пакеты (1 токен = 20 сек аудио)
- **Telegram Stars** — Нативная интеграция платежей с 4 пакетами
- **Тарифы пользователей** — Free, Paid, VIP, Tester, Admin, Blocked

### Интеграция с Obsidian
- **Синхронизация через GitHub** — Автосохранение транскрипций в ваш vault через GitHub API
- **OAuth Device Flow** — Безопасная аутентификация без раскрытия токенов
- **Автокатегоризация** — ИИ-классификация заметок с помощью Claude Haiku

### Привязка аккаунтов
- **Telegram ↔ WhatsApp** — Привязка аккаунтов по одноразовым кодам
- **Rate limiting** — Защита от перебора

### Администрирование
- **Панель администратора** — `/admin` хаб с inline-кнопками в Telegram
- **Управление пользователями** — Добавление/удаление VIP и тестеров, блокировка/разблокировка, пополнение токенов через Telegram
- **Статистика использования** — Транскрипции, доход, расходы за месяц
- **Мониторинг здоровья** — Алерты по использованию Wit.ai/Groq

## Требования

- Python 3.13+
- MongoDB
- FFmpeg (для обработки аудио)
- API токены [Wit.ai](https://wit.ai/)
- Токен Telegram бота от [@BotFather](https://t.me/BotFather)
- (Опционально) Данные WhatsApp Business API
- (Опционально) GitHub OAuth App client ID (для интеграции с Obsidian)
- (Опционально) [Groq](https://groq.com/) API ключ (для резервной транскрипции Whisper)
- (Опционально) [Anthropic](https://anthropic.com/) API ключ (для автокатегоризации)

## Быстрый старт

```bash
# Клонирование
git clone https://github.com/yastcher/evlampiy.git
cd evlampiy

# Установка зависимостей
pip install uv
uv sync

# Настройка
cp .env.example .env
# Отредактируйте .env, добавив токены

# Запуск
uv run python -m src.main
```

## Конфигурация

Создайте файл `.env`:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_бота
MONGO_URI=mongodb://localhost:27017/

# Токены Wit.ai (получить на https://wit.ai/)
WIT_EN_TOKEN=токен_английский
WIT_RU_TOKEN=токен_русский
WIT_ES_TOKEN=токен_испанский
WIT_DE_TOKEN=токен_немецкий

# Опционально: интеграция с GPT
GPT_TOKEN=ваш_openai_токен
GPT_MODEL=gpt-4o-mini

# Опционально: интеграция с WhatsApp (см. WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=ваш_whatsapp_токен
WHATSAPP_PHONE_ID=ваш_phone_id
WHATSAPP_VERIFY_TOKEN=ваш_verify_токен

# Опционально: GitHub OAuth (для интеграции с Obsidian)
# Для ручной настройки токена см. docs/GITHUB_TOKEN_SETUP.md
GITHUB_CLIENT_ID=ваш_github_oauth_app_client_id

# Опционально: Монетизация
GROQ_API_KEY=ваш_groq_api_ключ
VIP_USER_IDS=123456,789012   # env fallback; управление через /admin в Telegram
ADMIN_USER_IDS=123456789
FREE_MONTHLY_TOKENS=10
WIT_FREE_MONTHLY_LIMIT=500
```

Инструкции по настройке WhatsApp: [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md).

## Команды бота

| Команда     | Описание                                 |
|-------------|------------------------------------------|
| `/start`    | Показать справку и текущие настройки     |
| `/settings` | Язык, GPT команда и провайдер            |
| `/obsidian` | Синхронизация заметок с GitHub           |
| `/account`  | Баланс, токены и привязка WhatsApp        |

Команды администратора см. в [ADMIN.md](ADMIN.md).

## Разработка

### Подход

- **DDD** — Domain-driven design с чёткими границами модулей (`transcription/`, `telegram/`, `whatsapp/`)
- **TDD** — Сначала тесты, потом реализация
- **Trophy Testing** — Интеграционные тесты с реальной БД (mongomock), моки только на внешних границах

### Команды

```bash
# Установка dev-зависимостей
uv sync --group dev

# Запуск тестов
uv run pytest

# Запуск линтера
uv run ruff check

# Запуск с покрытием
uv run pytest --cov=src --cov-fail-under=85
```

## Деплой

См. [DEPLOY.md](../DEPLOY.md) для инструкций по развёртыванию в Docker.

## Лицензия

Проприетарная. Все права защищены. См. [LICENSE](../LICENSE).
