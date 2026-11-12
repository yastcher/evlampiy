# Admin Guide

[English](#english) | [Русский](#русский)

---

## English

### User Roles

| Role | Voice transcription | Provider | GPT/Categorization | Tokens |
|------|--------------------|---------|--------------------|--------|
| **Admin** | Unlimited | Groq (priority) | Unlimited | Not needed |
| **VIP** | Unlimited | Groq (priority) | Unlimited | Not needed |
| **Tester** | Unlimited | Wit.ai (Groq fallback) | Uses tokens | Admin top-up |
| **Paid** | Uses tokens | Wit.ai (Groq fallback) | Free | Purchase via Stars |
| **Free** | 10 free/month | Wit.ai only | Free | Purchase via Stars |
| **Blocked** | Denied | — | Denied | — |

### Configuration

Admin user IDs are configured in `.env` (cannot be changed at runtime):

```env
ADMIN_USER_IDS=123456789,987654321
```

VIP users can be configured in `.env` as fallback, but primarily managed via Telegram:

```env
VIP_USER_IDS=123456,789012
```

Get your Telegram user ID by messaging [@userinfobot](https://t.me/userinfobot).

### Admin Panel (`/admin`)

The `/admin` command opens an inline keyboard hub:

- **VIP users** — View current VIP list
- **Testers** — View current tester list
- **Blocked users** — View blocked user list
- **Stats** — System-wide statistics
- **Add credits** — Usage hint for `/add_credits`

### Admin Commands

| Command | Description |
|---------|-------------|
| `/admin` | Open admin panel with inline buttons |
| `/stats` | View system-wide statistics |
| `/add_vip <user_id>` | Add user to VIP list |
| `/remove_vip <user_id>` | Remove user from VIP list |
| `/add_tester <user_id>` | Add user to tester list |
| `/remove_tester <user_id>` | Remove user from tester list |
| `/add_credits <user_id> <amount>` | Top up tokens for a user |
| `/block <user_id>` | Block a user from using the bot |
| `/unblock <user_id>` | Unblock a user |

### Storage

- **Admin list** — `.env` only (`ADMIN_USER_IDS`)
- **VIP list** — MongoDB (primary) + `.env` fallback (`VIP_USER_IDS`)
- **Tester list** — MongoDB only (managed via `/add_tester`, `/remove_tester`)

### System Statistics (`/stats`)

Shows monthly metrics for administrators:

```
📊 System Stats (2026-01)

Users
• Total transcriptions: 1,234
• Payments: 12

Revenue
• Stars received: 89★
• Credits sold: 89
• Revenue: $1.25

Costs
• Wit.ai: 45 / 500 (9.0%)
• Groq audio: 3,400 sec/mo ($0.04) | limit: 7,200 sec/day

LLM Providers
• Categ: groq 30rpm ✅ → openrouter 10rpm ✅ → gemini 15rpm ✅
• GPT:   groq 30rpm ✅ → openrouter 10rpm ✅ → gemini 15rpm ✅
• Not in chain: anthropic

Health
• Wit.ai: ✅ OK
• Groq: ✅ Configured
```

The **LLM Providers** section shows the active provider chain with rate limits and key status. The **Not in chain** line only appears when a provider has a configured key but is not part of any fallback chain.

### Automatic Alerts

Admins receive automatic alerts for important events:

| Alert | Trigger | Priority |
|-------|---------|----------|
| First payment | First payment of the month | High |
| Revenue milestone | $10, $50, $100, $500, $1000 | Medium |
| Wit.ai warning | Usage > 80% of monthly limit | High |
| Wit.ai critical | Usage > 95% of monthly limit | Critical |

Alerts are sent once per month per event type (no duplicates).

### Monitoring

**Health check endpoint:**
```bash
curl http://localhost:8000/health
# {"status": "ok", "whatsapp": "on"}   (whatsapp: on | off | no app secret)
```

**Docker logs:**
```bash
docker compose logs -f evlampiy_bot
docker compose logs evlampiy_bot 2>&1 | grep ERROR
```

---

## Русский

### Роли пользователей

| Роль | Транскрипция голоса | Провайдер | GPT/Категоризация | Токены |
|------|--------------------|-----------|--------------------|--------|
| **Admin** | Безлимитно | Groq (приоритет) | Безлимитно | Не нужны |
| **VIP** | Безлимитно | Groq (приоритет) | Безлимитно | Не нужны |
| **Tester** | Безлимитно | Wit.ai (Groq резерв) | Расходуют токены | Пополняет админ |
| **Paid** | Расходуют токены | Wit.ai (Groq резерв) | Бесплатно | Покупка через Stars |
| **Free** | 10 бесплатных/мес | Только Wit.ai | Бесплатно | Покупка через Stars |
| **Blocked** | Запрещено | — | Запрещено | — |

### Конфигурация

ID администраторов задаются в `.env` (нельзя изменить в рантайме):

```env
ADMIN_USER_IDS=123456789,987654321
```

VIP-пользователи могут быть заданы в `.env` как fallback, но управляются через Telegram:

```env
VIP_USER_IDS=123456,789012
```

Узнайте свой Telegram user ID через [@userinfobot](https://t.me/userinfobot).

### Панель администратора (`/admin`)

Команда `/admin` открывает хаб с inline-кнопками:

- **VIP пользователи** — Текущий список VIP
- **Тестеры** — Текущий список тестеров
- **Заблокированные** — Список заблокированных пользователей
- **Статистика** — Системная статистика
- **Начислить кредиты** — Подсказка по использованию `/add_credits`

### Команды администратора

| Команда | Описание |
|---------|----------|
| `/admin` | Открыть панель администратора |
| `/stats` | Просмотр системной статистики |
| `/add_vip <user_id>` | Добавить пользователя в VIP |
| `/remove_vip <user_id>` | Удалить пользователя из VIP |
| `/add_tester <user_id>` | Добавить пользователя в тестеры |
| `/remove_tester <user_id>` | Удалить пользователя из тестеров |
| `/add_credits <user_id> <amount>` | Начислить токены пользователю |
| `/block <user_id>` | Заблокировать пользователя |
| `/unblock <user_id>` | Разблокировать пользователя |

### Хранение

- **Список админов** — только `.env` (`ADMIN_USER_IDS`)
- **Список VIP** — MongoDB (основное) + `.env` fallback (`VIP_USER_IDS`)
- **Список тестеров** — только MongoDB (управление через `/add_tester`, `/remove_tester`)

### Системная статистика (`/stats`)

Показывает месячные метрики для администраторов:

```
📊 System Stats (2026-01)

Users
• Total transcriptions: 1,234
• Payments: 12

Revenue
• Stars received: 89★
• Credits sold: 89
• Revenue: $1.25

Costs
• Wit.ai: 45 / 500 (9.0%)
• Groq audio: 3,400 sec/mo ($0.04) | limit: 7,200 sec/day

LLM Providers
• Categ: groq 30rpm ✅ → openrouter 10rpm ✅ → gemini 15rpm ✅
• GPT:   groq 30rpm ✅ → openrouter 10rpm ✅ → gemini 15rpm ✅
• Not in chain: anthropic

Health
• Wit.ai: ✅ OK
• Groq: ✅ Configured
```

### Автоматические алерты

Администраторы получают автоматические уведомления о важных событиях:

| Алерт | Триггер | Приоритет |
|-------|---------|-----------|
| Первый платёж | Первый платёж месяца | Высокий |
| Milestone дохода | $10, $50, $100, $500, $1000 | Средний |
| Wit.ai предупреждение | Использование > 80% лимита | Высокий |
| Wit.ai критический | Использование > 95% лимита | Критический |

Алерты отправляются один раз в месяц на каждый тип события (без дублирования).

### Мониторинг

**Health check endpoint:**
```bash
curl http://localhost:8000/health
# {"status": "ok", "whatsapp": "on"}   (whatsapp: on | off | no app secret)
```

**Логи Docker:**
```bash
docker compose logs -f evlampiy_bot
docker compose logs evlampiy_bot 2>&1 | grep ERROR
```
