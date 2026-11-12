# Admin Guide

[English](#english) | [Русский](#русский)

---

## English

### User Roles

| Role | Voice transcription | Provider | GPT/Categorization | Tokens |
|------|--------------------|---------|--------------------|--------|
| **Admin** | Unlimited | Wit.ai (Groq by choice or past the Wit limit) | Free | Not needed |
| **VIP** | Unlimited | Wit.ai (Groq by choice or past the Wit limit) | Free | Not needed |
| **Tester** | Unlimited | Wit.ai (Groq by choice or past the Wit limit) | Free | Not needed |
| **Paid** | Uses tokens | Wit.ai (Groq by choice or past the Wit limit) | Free | Purchase via Stars |
| **Free** | 10 free/month | Wit.ai only | Free | Purchase via Stars |
| **Blocked** | Denied | — | Denied | — |

A WhatsApp number linked to a Telegram account has that account's role (ADR-001).

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
- **LLM Providers** — The first provider of each chain, categorization and GPT: openrouter, gemini or groq

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
• Tokens sold: 104
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

Revenue is the Telegram Stars received × $0.014: a package sells more tokens than Stars. Stars are recorded since 2026-11-12.

The **LLM Providers** section shows the active provider chain with rate limits and key status. The **Not in chain** line only appears when a provider has a configured key but is not part of any fallback chain.

### Automatic Alerts

Admins receive automatic alerts for important events:

| Alert | Trigger | Priority |
|-------|---------|----------|
| First payment | First payment of the month | High |
| Revenue milestone | A payment takes the month's revenue in Stars past $10, $50, $100, $500 or $1000 | Medium |
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
| **Admin** | Безлимитно | Wit.ai (Groq по выбору или сверх лимита Wit) | Бесплатно | Не нужны |
| **VIP** | Безлимитно | Wit.ai (Groq по выбору или сверх лимита Wit) | Бесплатно | Не нужны |
| **Tester** | Безлимитно | Wit.ai (Groq по выбору или сверх лимита Wit) | Бесплатно | Не нужны |
| **Paid** | Расходуют токены | Wit.ai (Groq по выбору или сверх лимита Wit) | Бесплатно | Покупка через Stars |
| **Free** | 10 бесплатных/мес | Только Wit.ai | Бесплатно | Покупка через Stars |
| **Blocked** | Запрещено | — | Запрещено | — |

Привязанный номер WhatsApp получает роль своего аккаунта Telegram (ADR-001).

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
- **LLM Providers** — Первый провайдер каждой цепочки, категоризации и GPT: openrouter, gemini или groq

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
• Tokens sold: 104
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

Доход — полученные Telegram Stars × $0,014: пакет продаёт больше токенов, чем звёзд. Звёзды записываются с 2026-11-12.

### Автоматические алерты

Администраторы получают автоматические уведомления о важных событиях:

| Алерт | Триггер | Приоритет |
|-------|---------|-----------|
| Первый платёж | Первый платёж месяца | Высокий |
| Milestone дохода | Платёж переводит доход месяца в звёздах через $10, $50, $100, $500 или $1000 | Средний |
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
