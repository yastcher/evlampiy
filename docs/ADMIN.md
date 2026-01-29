# Admin Guide

[English](#english) | [Русский](#русский)

---

## English

### Admin Role

Admins have unlimited access to transcription services (same as VIP users) and can view system statistics.

### Configuration

Add admin user IDs to `.env`:

```env
ADMIN_USER_IDS=123456789,987654321
```

Get your Telegram user ID by messaging [@userinfobot](https://t.me/userinfobot).

### Admin Commands

| Command   | Description                          |
|-----------|--------------------------------------|
| `/stats`  | View system-wide statistics          |

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
• Wit.ai: 45,230 / 1,000,000 (4.5%)
• Groq: 3,400 sec ($0.04)

Health
• Wit.ai: ✅ OK
• Groq: ✅ Configured
```

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
# {"status": "ok"}
```

**Docker logs:**
```bash
docker compose logs -f evlampiy_bot
docker compose logs evlampiy_bot 2>&1 | grep ERROR
```

---

## Русский

### Роль администратора

Администраторы имеют безлимитный доступ к сервису транскрипции (как VIP) и могут просматривать системную статистику.

### Конфигурация

Добавьте ID администраторов в `.env`:

```env
ADMIN_USER_IDS=123456789,987654321
```

Узнайте свой Telegram user ID через [@userinfobot](https://t.me/userinfobot).

### Команды администратора

| Команда   | Описание                             |
|-----------|--------------------------------------|
| `/stats`  | Просмотр системной статистики        |

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
• Wit.ai: 45,230 / 1,000,000 (4.5%)
• Groq: 3,400 sec ($0.04)

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
# {"status": "ok"}
```

**Логи Docker:**
```bash
docker compose logs -f evlampiy_bot
docker compose logs evlampiy_bot 2>&1 | grep ERROR
```
