# WhatsApp Business API Setup

[Русский](#настройка-whatsapp-business-api) | [English](#english)

---

## English

### Prerequisites

- Facebook account
- Meta Business account (free)
- Phone number for WhatsApp (can be a new number, not linked to personal WhatsApp)

### Step 1: Create Meta Developer Account

1. Go to [developers.facebook.com](https://developers.facebook.com/)
2. Click "Get Started" and log in with your Facebook account
3. Accept the developer terms

### Step 2: Create a Meta App

1. Go to [developers.facebook.com/apps](https://developers.facebook.com/apps/)
2. Click "Create App"
3. Select "Business" type
4. Enter app name (e.g., "Evlampiy Bot")
5. Select or create a Business Portfolio
6. Click "Create App"

### Step 3: Add WhatsApp Product

1. In your app dashboard, find "Add Products"
2. Click "Set Up" on WhatsApp
3. You'll be redirected to WhatsApp configuration

### Step 4: Get API Credentials

In WhatsApp > API Setup, you'll find:

| Credential                       | Location                   | Environment Variable |
|----------------------------------|----------------------------|----------------------|
| **Temporary Access Token**       | API Setup page (valid 24h) | `WHATSAPP_TOKEN`     |
| **Phone Number ID**              | API Setup > From           | `WHATSAPP_PHONE_ID`  |
| **WhatsApp Business Account ID** | API Setup page             | (optional)           |

### Step 5: Create Permanent Access Token

Temporary tokens expire in 24 hours. For production:

1. Go to [Business Settings](https://business.facebook.com/settings/system-users)
2. Create a System User with Admin role
3. Add your app with full control
4. Generate token with permissions:
    - `whatsapp_business_management`
    - `whatsapp_business_messaging`

### Step 6: Configure Webhook

1. In WhatsApp > Configuration > Webhook
2. Set Callback URL: `https://your-domain.com/` (pywa handles the path)
3. Set Verify Token: any string you choose → `WHATSAPP_VERIFY_TOKEN`
4. Subscribe to fields:
    - `messages`

### Step 7: Add Phone Number (Production)

For testing, Meta provides a test phone number. For production:

1. Go to WhatsApp > Phone Numbers
2. Add your business phone number
3. Verify via SMS or voice call
4. Wait for Meta approval (usually instant for personal use)

### Environment Variables

```env
# Required
WHATSAPP_TOKEN=your_permanent_access_token
WHATSAPP_PHONE_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token

# Optional (for token refresh)
WHATSAPP_APP_ID=your_app_id
WHATSAPP_APP_SECRET=your_app_secret
```

### Testing

1. In API Setup, add your phone number to "To" recipients
2. Send a test message from Meta's dashboard
3. Send a voice message to your WhatsApp Business number
4. Check bot logs for transcription

### Useful Links

- [WhatsApp Cloud API Docs](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Meta Business Help](https://www.facebook.com/business/help)
- [pywa Documentation](https://pywa.readthedocs.io/)

---

## Настройка WhatsApp Business API

### Требования

- Аккаунт Facebook
- Аккаунт Meta Business (бесплатно)
- Номер телефона для WhatsApp (может быть новый, не связанный с личным WhatsApp)

### Шаг 1: Создание аккаунта разработчика Meta

1. Перейдите на [developers.facebook.com](https://developers.facebook.com/)
2. Нажмите "Начать" и войдите через Facebook
3. Примите условия разработчика

### Шаг 2: Создание приложения Meta

1. Перейдите в [developers.facebook.com/apps](https://developers.facebook.com/apps/)
2. Нажмите "Создать приложение"
3. Выберите тип "Бизнес"
4. Введите название (например, "Evlampiy Bot")
5. Выберите или создайте Бизнес-портфолио
6. Нажмите "Создать приложение"

### Шаг 3: Добавление продукта WhatsApp

1. В панели приложения найдите "Добавить продукты"
2. Нажмите "Настроить" на WhatsApp
3. Вы будете перенаправлены в настройки WhatsApp

### Шаг 4: Получение API-данных

В WhatsApp > Настройка API вы найдёте:

| Данные                           | Расположение                 | Переменная окружения |
|----------------------------------|------------------------------|----------------------|
| **Временный токен**              | Страница настройки API (24ч) | `WHATSAPP_TOKEN`     |
| **Phone Number ID**              | Настройка API > От           | `WHATSAPP_PHONE_ID`  |
| **WhatsApp Business Account ID** | Страница настройки           | (опционально)        |

### Шаг 5: Создание постоянного токена

Временные токены истекают через 24 часа. Для продакшена:

1. Перейдите в [Настройки бизнеса](https://business.facebook.com/settings/system-users)
2. Создайте системного пользователя с ролью Администратор
3. Добавьте приложение с полным доступом
4. Сгенерируйте токен с разрешениями:
    - `whatsapp_business_management`
    - `whatsapp_business_messaging`

### Шаг 6: Настройка Webhook

1. В WhatsApp > Конфигурация > Webhook
2. URL обратного вызова: `https://ваш-домен.com/` (pywa обрабатывает путь)
3. Токен подтверждения: любая строка → `WHATSAPP_VERIFY_TOKEN`
4. Подпишитесь на поля:
    - `messages`

### Шаг 7: Добавление номера телефона (Продакшен)

Для тестирования Meta предоставляет тестовый номер. Для продакшена:

1. Перейдите в WhatsApp > Номера телефонов
2. Добавьте ваш бизнес-номер
3. Подтвердите через SMS или звонок
4. Дождитесь одобрения Meta (обычно мгновенно)

### Переменные окружения

```env
# Обязательные
WHATSAPP_TOKEN=ваш_постоянный_токен
WHATSAPP_PHONE_ID=ваш_phone_number_id
WHATSAPP_VERIFY_TOKEN=ваш_токен_верификации_webhook

# Опциональные (для обновления токена)
WHATSAPP_APP_ID=ваш_app_id
WHATSAPP_APP_SECRET=ваш_app_secret
```

### Тестирование

1. В настройке API добавьте свой номер в получатели "Кому"
2. Отправьте тестовое сообщение из панели Meta
3. Отправьте голосовое сообщение на ваш WhatsApp Business номер
4. Проверьте логи бота на наличие транскрипции

### Полезные ссылки

- [Документация WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Справка Meta Business](https://www.facebook.com/business/help)
- [Документация pywa](https://pywa.readthedocs.io/)
