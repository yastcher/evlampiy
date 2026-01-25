# Evlampiy Notes Bot

[![CI](https://github.com/YastYa/evlampiy_notes_tgbot/actions/workflows/deploy.yml/badge.svg)](https://github.com/YastYa/evlampiy_notes_tgbot/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](https://github.com/YastYa/evlampiy_notes_tgbot)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Русский | [English](../README.md)

Telegram-бот для транскрипции голосовых сообщений с поддержкой нескольких языков.

**Попробовать:** https://t.me/evlampiy_notes_bot

## Возможности

- **Транскрипция голоса** — Преобразование голосовых сообщений в текст через [Wit.ai](https://wit.ai/)
- **Мультиязычность** — Поддержка английского, немецкого, русского, испанского
- **Настройки по чатам** — Каждый пользователь/группа может иметь свой язык
- **Интеграция с GPT** — Вызов GPT голосом (скажите "евлампий" + ваш вопрос)
- **Экспорт в Obsidian** — Сохранение заметок в Obsidian через GitHub

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
└── whatsapp/            # Адаптер WhatsApp (скоро)
```

## Требования

- Python 3.12+
- MongoDB
- FFmpeg (для обработки аудио)
- API токены [Wit.ai](https://wit.ai/)
- Токен Telegram бота от [@BotFather](https://t.me/BotFather)

## Быстрый старт

```bash
# Клонирование
git clone https://github.com/YastYa/evlampiy_notes_tgbot.git
cd evlampiy_notes_tgbot

# Установка зависимостей
pip install uv
uv sync

# Настройка
cp .env.example .env
# Отредактируйте .env, добавив токены

# Запуск
uv run python main.py
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
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Показать справку и текущие настройки |
| `/choose_your_language` | Выбрать язык распознавания |
| `/enter_your_command` | Задать слово-триггер для GPT |

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
- [x] Интеграция с GPT
- [x] CI/CD через GitHub Actions
- [ ] Интеграция с WhatsApp
- [ ] Улучшения экспорта в Obsidian
- [ ] Классификация сообщений по темам

## Лицензия

[GPL-3.0](../LICENSE)
