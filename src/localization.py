from src.config import ENGLISH, GERMAN, RUSSIAN, SPANISH

translates = {
    "success": {
        ENGLISH: "Success",
        GERMAN: "Erfolg",
        RUSSIAN: "Успешно",
        SPANISH: "Éxito",
    },
    "not_found": {
        ENGLISH: "Not found",
        GERMAN: "Nicht gefunden",
        RUSSIAN: "Не найден",
        SPANISH: "No encontrado",
    },
    "error_connection": {
        ENGLISH: "Connection error. Try later",
        GERMAN: "Verbindungsfehler. Versuchen Sie es später",
        RUSSIAN: "Ошибка соединения. Попробуйте позднее",
        SPANISH: "Error de conexión. Inténtalo más tarde",
    },
    "bad_data": {
        ENGLISH: "Bad data",
        GERMAN: "Schlechte Daten",
        RUSSIAN: "Неверные данные",
        SPANISH: "Datos incorrectos",
    },
    "choose_my_language": {
        ENGLISH: "Selected language: English",
        GERMAN: "Ausgewählte Sprache: Deutsch",
        RUSSIAN: "Выбранный язык: Русский",
        SPANISH: "Idioma seleccionado: Español",
    },
    "start_message": {
        ENGLISH: (
            "🎙 <b>Voice-to-Text Bot</b>\n\n"
            "Send a voice message — get text back instantly.\n\n"
            "<b>Features:</b>\n"
            "• Multi-language transcription (en, ru, es, de)\n"
            "• Sync notes to Obsidian via GitHub\n"
            "• AI categorization of notes\n"
            "• Link your WhatsApp account\n\n"
            "<b>Current settings:</b>\n"
            "Language: {chat_language}\n"
            "GPT trigger: {gpt_command}\n\n"
            "<b>Menu:</b>\n"
            "/settings - Language & GPT command\n"
            "/obsidian - Notes sync to GitHub\n"
            "/account - Balance, credits & WhatsApp"
        ),
        GERMAN: (
            "🎙 <b>Sprache-zu-Text Bot</b>\n\n"
            "Sende eine Sprachnachricht — erhalte sofort Text.\n\n"
            "<b>Funktionen:</b>\n"
            "• Mehrsprachige Transkription (en, ru, es, de)\n"
            "• Notizen mit Obsidian über GitHub synchronisieren\n"
            "• KI-Kategorisierung von Notizen\n"
            "• WhatsApp-Konto verknüpfen\n\n"
            "<b>Aktuelle Einstellungen:</b>\n"
            "Sprache: {chat_language}\n"
            "GPT-Trigger: {gpt_command}\n\n"
            "<b>Menü:</b>\n"
            "/settings - Sprache & GPT-Befehl\n"
            "/obsidian - Notizen-Sync mit GitHub\n"
            "/account - Guthaben, Credits & WhatsApp"
        ),
        RUSSIAN: (
            "🎙 <b>Голос в текст</b>\n\n"
            "Отправьте голосовое сообщение — получите текст мгновенно.\n\n"
            "<b>Возможности:</b>\n"
            "• Транскрипция на 4 языках (en, ru, es, de)\n"
            "• Синхронизация заметок в Obsidian через GitHub\n"
            "• ИИ-категоризация заметок\n"
            "• Привязка WhatsApp аккаунта\n\n"
            "<b>Текущие настройки:</b>\n"
            "Язык: {chat_language}\n"
            "Триггер GPT: {gpt_command}\n\n"
            "<b>Меню:</b>\n"
            "/settings - Язык и GPT команда\n"
            "/obsidian - Синхронизация с GitHub\n"
            "/account - Баланс, кредиты и WhatsApp"
        ),
        SPANISH: (
            "🎙 <b>Bot de Voz a Texto</b>\n\n"
            "Envía un mensaje de voz — recibe texto al instante.\n\n"
            "<b>Funciones:</b>\n"
            "• Transcripción multilingüe (en, ru, es, de)\n"
            "• Sincronizar notas con Obsidian vía GitHub\n"
            "• Categorización de notas con IA\n"
            "• Vincular tu cuenta de WhatsApp\n\n"
            "<b>Configuración actual:</b>\n"
            "Idioma: {chat_language}\n"
            "Activador GPT: {gpt_command}\n\n"
            "<b>Menú:</b>\n"
            "/settings - Idioma y comando GPT\n"
            "/obsidian - Sincronización con GitHub\n"
            "/account - Saldo, créditos y WhatsApp"
        ),
    },
    "insufficient_credits": {
        ENGLISH: "Not enough credits. Use /buy to purchase more.",
        GERMAN: "Nicht genügend Credits. Verwenden Sie /buy, um mehr zu kaufen.",
        RUSSIAN: "Недостаточно кредитов. Используйте /buy для покупки.",
        SPANISH: "No tienes suficientes créditos. Usa /buy para comprar más.",
    },
    "service_unavailable": {
        ENGLISH: "Transcription service is temporarily unavailable. Please try again later.",
        GERMAN: "Transkriptionsdienst ist vorübergehend nicht verfügbar. Bitte versuchen Sie es später erneut.",
        RUSSIAN: "Сервис транскрипции временно недоступен. Попробуйте позже.",
        SPANISH: "El servicio de transcripción no está disponible temporalmente. Inténtalo más tarde.",
    },
    "categorize_enabled": {
        ENGLISH: "Auto-categorization enabled.",
        GERMAN: "Automatische Kategorisierung aktiviert.",
        RUSSIAN: "Автокатегоризация включена.",
        SPANISH: "Categorización automática activada.",
    },
    "categorize_disabled": {
        ENGLISH: "Auto-categorization disabled.",
        GERMAN: "Automatische Kategorisierung deaktiviert.",
        RUSSIAN: "Автокатегоризация выключена.",
        SPANISH: "Categorización automática desactivada.",
    },
    "categorize_done": {
        ENGLISH: "Categorized {count} notes.",
        GERMAN: "{count} Notizen kategorisiert.",
        RUSSIAN: "Категоризировано заметок: {count}.",
        SPANISH: "{count} notas categorizadas.",
    },
    "categorize_no_files": {
        ENGLISH: "No files to categorize in income folder.",
        GERMAN: "Keine Dateien zum Kategorisieren im Eingangsordner.",
        RUSSIAN: "Нет файлов для категоризации в папке income.",
        SPANISH: "No hay archivos para categorizar en la carpeta de entrada.",
    },
    "mystats_message": {
        ENGLISH: (
            "📊 <b>Your Statistics</b>\n\n"
            "Balance: {credits} credits\n"
            "Tier: {tier}\n\n"
            "<b>All time:</b>\n"
            "• Transcriptions: {total_transcriptions}\n"
            "• Credits spent: {total_spent}\n"
            "• Credits purchased: {total_purchased}"
        ),
        GERMAN: (
            "📊 <b>Ihre Statistiken</b>\n\n"
            "Guthaben: {credits} Credits\n"
            "Stufe: {tier}\n\n"
            "<b>Insgesamt:</b>\n"
            "• Transkriptionen: {total_transcriptions}\n"
            "• Credits ausgegeben: {total_spent}\n"
            "• Credits gekauft: {total_purchased}"
        ),
        RUSSIAN: (
            "📊 <b>Ваша статистика</b>\n\n"
            "Баланс: {credits} кредитов\n"
            "Тариф: {tier}\n\n"
            "<b>За всё время:</b>\n"
            "• Транскрипций: {total_transcriptions}\n"
            "• Потрачено кредитов: {total_spent}\n"
            "• Куплено кредитов: {total_purchased}"
        ),
        SPANISH: (
            "📊 <b>Tus estadísticas</b>\n\n"
            "Saldo: {credits} créditos\n"
            "Nivel: {tier}\n\n"
            "<b>Total:</b>\n"
            "• Transcripciones: {total_transcriptions}\n"
            "• Créditos gastados: {total_spent}\n"
            "• Créditos comprados: {total_purchased}"
        ),
    },
    # Hub titles
    "settings_hub_title": {
        ENGLISH: "⚙️ Settings",
        GERMAN: "⚙️ Einstellungen",
        RUSSIAN: "⚙️ Настройки",
        SPANISH: "⚙️ Configuración",
    },
    "obsidian_hub_title": {
        ENGLISH: "📝 Notes",
        GERMAN: "📝 Notizen",
        RUSSIAN: "📝 Заметки",
        SPANISH: "📝 Notas",
    },
    "account_hub_title": {
        ENGLISH: "💰 Account",
        GERMAN: "💰 Konto",
        RUSSIAN: "💰 Аккаунт",
        SPANISH: "💰 Cuenta",
    },
    # Hub button labels
    "btn_language": {
        ENGLISH: "🌐 Language",
        GERMAN: "🌐 Sprache",
        RUSSIAN: "🌐 Язык",
        SPANISH: "🌐 Idioma",
    },
    "btn_gpt_command": {
        ENGLISH: "🤖 GPT command",
        GERMAN: "🤖 GPT-Befehl",
        RUSSIAN: "🤖 GPT команда",
        SPANISH: "🤖 Comando GPT",
    },
    "btn_connect_github": {
        ENGLISH: "🔗 Connect GitHub",
        GERMAN: "🔗 GitHub verbinden",
        RUSSIAN: "🔗 Подключить GitHub",
        SPANISH: "🔗 Conectar GitHub",
    },
    "btn_toggle_sync_on": {
        ENGLISH: "🔄 Sync: ON",
        GERMAN: "🔄 Sync: AN",
        RUSSIAN: "🔄 Синхр.: ВКЛ",
        SPANISH: "🔄 Sincr.: SÍ",
    },
    "btn_toggle_sync_off": {
        ENGLISH: "🔄 Sync: OFF",
        GERMAN: "🔄 Sync: AUS",
        RUSSIAN: "🔄 Синхр.: ВЫКЛ",
        SPANISH: "🔄 Sincr.: NO",
    },
    "btn_toggle_sort_on": {
        ENGLISH: "📂 Auto-sort: ON",
        GERMAN: "📂 Auto-Sort: AN",
        RUSSIAN: "📂 Авто-сорт.: ВКЛ",
        SPANISH: "📂 Auto-orden: SÍ",
    },
    "btn_toggle_sort_off": {
        ENGLISH: "📂 Auto-sort: OFF",
        GERMAN: "📂 Auto-Sort: AUS",
        RUSSIAN: "📂 Авто-сорт.: ВЫКЛ",
        SPANISH: "📂 Auto-orden: NO",
    },
    "btn_categorize_all": {
        ENGLISH: "📂 Categorize all",
        GERMAN: "📂 Alle kategorisieren",
        RUSSIAN: "📂 Категоризировать всё",
        SPANISH: "📂 Categorizar todo",
    },
    "btn_disconnect_github": {
        ENGLISH: "❌ Disconnect GitHub",
        GERMAN: "❌ GitHub trennen",
        RUSSIAN: "❌ Отключить GitHub",
        SPANISH: "❌ Desconectar GitHub",
    },
    "btn_buy": {
        ENGLISH: "💳 Buy credits",
        GERMAN: "💳 Credits kaufen",
        RUSSIAN: "💳 Купить кредиты",
        SPANISH: "💳 Comprar créditos",
    },
    "btn_balance": {
        ENGLISH: "💰 Balance",
        GERMAN: "💰 Guthaben",
        RUSSIAN: "💰 Баланс",
        SPANISH: "💰 Saldo",
    },
    "btn_mystats": {
        ENGLISH: "📊 My stats",
        GERMAN: "📊 Meine Statistiken",
        RUSSIAN: "📊 Моя статистика",
        SPANISH: "📊 Mis estadísticas",
    },
    "btn_link_whatsapp": {
        ENGLISH: "📱 Link WhatsApp",
        GERMAN: "📱 WhatsApp verknüpfen",
        RUSSIAN: "📱 Привязать WhatsApp",
        SPANISH: "📱 Vincular WhatsApp",
    },
    "btn_unlink_whatsapp": {
        ENGLISH: "📱 Unlink WhatsApp",
        GERMAN: "📱 WhatsApp trennen",
        RUSSIAN: "📱 Отвязать WhatsApp",
        SPANISH: "📱 Desvincular WhatsApp",
    },
}
