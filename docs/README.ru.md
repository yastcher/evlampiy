# Evlampiy Notes Bot

[![CI](https://github.com/yastcher/evlampiy/actions/workflows/deploy.yml/badge.svg)](https://github.com/yastcher/evlampiy/actions)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](https://github.com/yastcher/evlampiy)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](../LICENSE)

[English](../README.md) | Русский | [Español](README.es.md) | [Deutsch](README.de.md)

Telegram и WhatsApp бот для транскрипции голосовых сообщений с поддержкой нескольких языков.

**Попробовать:** https://t.me/evlampiy_notes_bot

## Возможности

- **Транскрипция голоса** — Преобразование голосовых сообщений в текст через [Wit.ai](https://wit.ai/)
- **Мультиплатформенность** — Работает с Telegram и WhatsApp
- **Мультиязычность** — Поддержка английского, немецкого, русского, испанского
- **Настройки по чатам** — Каждый пользователь/группа может иметь свой язык
- **Интеграция с GPT** — Вызов GPT голосом (скажите "евлампий" + ваш вопрос)
- **Интеграция с Obsidian** — Автосохранение транскрипций голосовых в Obsidian через GitHub (OAuth Device Flow)

## Архитектура

```
src/
├── transcription/       # Domain-слой (независим от платформы)
│   ├── service.py       # Логика транскрипции
│   └── wit_client.py    # Клиенты Wit.ai
├── telegram/            # Адаптер Telegram
│   ├── bot.py
│   ├── handlers.py
│   └── voice.py
├── whatsapp/            # Адаптер WhatsApp
│   ├── client.py
│   └── handlers.py
├── github_oauth.py      # GitHub OAuth Device Flow
├── github_api.py        # Операции GitHub API
├── obsidian.py          # Интеграция с Obsidian
└── main.py              # Точка входа
```

## Требования

- Python 3.12+
- MongoDB
- FFmpeg (для обработки аудио)
- API токены [Wit.ai](https://wit.ai/)
- Токен Telegram бота от [@BotFather](https://t.me/BotFather)
- (Опционально) Данные WhatsApp Business API
- (Опционально) GitHub OAuth App client ID (для интеграции с Obsidian)

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

# Опционально: интеграция с WhatsApp (см. WHATSAPP_SETUP.md)
WHATSAPP_TOKEN=ваш_whatsapp_токен
WHATSAPP_PHONE_ID=ваш_phone_id
WHATSAPP_VERIFY_TOKEN=ваш_verify_токен

# Опционально: GitHub OAuth (для интеграции с Obsidian)
GITHUB_CLIENT_ID=ваш_github_oauth_app_client_id
```

Инструкции по настройке WhatsApp: [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md).

## Команды бота

| Команда                 | Описание                                     |
|-------------------------|----------------------------------------------|
| `/start`                | Показать справку и текущие настройки         |
| `/choose_your_language` | Выбрать язык распознавания                   |
| `/enter_your_command`   | Задать слово-триггер для GPT                 |
| `/connect_github`       | Подключить GitHub аккаунт (OAuth Device Flow)|
| `/toggle_obsidian`      | Включить/выключить синхронизацию с Obsidian  |
| `/disconnect_github`    | Отключить GitHub и синхронизацию             |

## Разработка

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

## Roadmap

- [x] Транскрипция голоса в текст
- [x] Мультиязычность (EN, RU, ES, DE)
- [ ] Интеграция с GPT
- [x] CI/CD через GitHub Actions
- [x] Интеграция с WhatsApp
- [x] Интеграция с Obsidian через GitHub OAuth
- [ ] Классификация сообщений по темам

## Лицензия

Проприетарная. Все права защищены. См. [LICENSE](../LICENSE).
