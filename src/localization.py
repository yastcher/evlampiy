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
    # Handler responses
    "choose_language_prompt": {
        ENGLISH: "Please choose your preferred language:",
        GERMAN: "Bitte wählen Sie Ihre bevorzugte Sprache:",
        RUSSIAN: "Выберите предпочтительный язык:",
        SPANISH: "Por favor, elige tu idioma preferido:",
    },
    "obsidian_sync_enabled": {
        ENGLISH: "Obsidian sync is now enabled.",
        GERMAN: "Obsidian-Sync ist jetzt aktiviert.",
        RUSSIAN: "Синхронизация с Obsidian включена.",
        SPANISH: "Sincronización con Obsidian activada.",
    },
    "obsidian_sync_disabled": {
        ENGLISH: "Obsidian sync is now disabled.",
        GERMAN: "Obsidian-Sync ist jetzt deaktiviert.",
        RUSSIAN: "Синхронизация с Obsidian выключена.",
        SPANISH: "Sincronización con Obsidian desactivada.",
    },
    "github_disconnected": {
        ENGLISH: "GitHub disconnected. Obsidian sync disabled.",
        GERMAN: "GitHub getrennt. Obsidian-Sync deaktiviert.",
        RUSSIAN: "GitHub отключён. Синхронизация выключена.",
        SPANISH: "GitHub desconectado. Sincronización desactivada.",
    },
    "github_not_connected": {
        ENGLISH: "GitHub not connected. Use /connect_github first.",
        GERMAN: "GitHub nicht verbunden. Verwenden Sie zuerst /connect_github.",
        RUSSIAN: "GitHub не подключён. Используйте /connect_github.",
        SPANISH: "GitHub no conectado. Usa /connect_github primero.",
    },
    "github_auth_failed": {
        ENGLISH: "Failed to start GitHub authorization.",
        GERMAN: "GitHub-Autorisierung konnte nicht gestartet werden.",
        RUSSIAN: "Не удалось начать авторизацию GitHub.",
        SPANISH: "Error al iniciar la autorización de GitHub.",
    },
    "github_auth_prompt": {
        ENGLISH: (
            "1) Open: {verification_uri}\n"
            "2) Enter code: {user_code}\n\n"
            "You have {expires_in} seconds to complete authorization."
        ),
        GERMAN: (
            "1) Öffnen: {verification_uri}\n"
            "2) Code eingeben: {user_code}\n\n"
            "Sie haben {expires_in} Sekunden zur Autorisierung."
        ),
        RUSSIAN: (
            "1) Откройте: {verification_uri}\n"
            "2) Введите код: {user_code}\n\n"
            "На авторизацию отведено {expires_in} секунд."
        ),
        SPANISH: (
            "1) Abre: {verification_uri}\n"
            "2) Ingresa el código: {user_code}\n\n"
            "Tienes {expires_in} segundos para completar la autorización."
        ),
    },
    "github_auth_timeout": {
        ENGLISH: "GitHub authorization failed or timed out. Try /connect_github again.",
        GERMAN: "GitHub-Autorisierung fehlgeschlagen oder abgelaufen. Versuchen Sie /connect_github erneut.",
        RUSSIAN: "Авторизация GitHub не удалась или истекло время. Попробуйте /connect_github снова.",
        SPANISH: "Autorización de GitHub fallida o expirada. Intenta /connect_github de nuevo.",
    },
    "github_repo_failed": {
        ENGLISH: "Failed to create/access GitHub repository.",
        GERMAN: "GitHub-Repository konnte nicht erstellt/zugegriffen werden.",
        RUSSIAN: "Не удалось создать/получить доступ к репозиторию GitHub.",
        SPANISH: "Error al crear/acceder al repositorio de GitHub.",
    },
    "github_connected": {
        ENGLISH: "GitHub connected! Repository: {owner}/{repo}\nObsidian sync is now enabled.",
        GERMAN: "GitHub verbunden! Repository: {owner}/{repo}\nObsidian-Sync ist jetzt aktiviert.",
        RUSSIAN: "GitHub подключён! Репозиторий: {owner}/{repo}\nСинхронизация с Obsidian включена.",
        SPANISH: "¡GitHub conectado! Repositorio: {owner}/{repo}\nSincronización con Obsidian activada.",
    },
    "whatsapp_link_prompt": {
        ENGLISH: "Send this message to the bot on WhatsApp:\n\nlink {code}\n\nCode expires in 5 minutes.",
        GERMAN: "Senden Sie diese Nachricht an den Bot auf WhatsApp:\n\nlink {code}\n\nCode läuft in 5 Minuten ab.",
        RUSSIAN: "Отправьте это сообщение боту в WhatsApp:\n\nlink {code}\n\nКод действителен 5 минут.",
        SPANISH: "Envía este mensaje al bot en WhatsApp:\n\nlink {code}\n\nEl código expira en 5 minutos.",
    },
    "whatsapp_unlinked": {
        ENGLISH: "WhatsApp account unlinked.",
        GERMAN: "WhatsApp-Konto getrennt.",
        RUSSIAN: "Аккаунт WhatsApp отвязан.",
        SPANISH: "Cuenta de WhatsApp desvinculada.",
    },
    "whatsapp_not_linked": {
        ENGLISH: "No WhatsApp account linked.",
        GERMAN: "Kein WhatsApp-Konto verknüpft.",
        RUSSIAN: "Аккаунт WhatsApp не привязан.",
        SPANISH: "No hay cuenta de WhatsApp vinculada.",
    },
    "balance_message": {
        ENGLISH: "Balance: {credits} credits",
        GERMAN: "Guthaben: {credits} Credits",
        RUSSIAN: "Баланс: {credits} кредитов",
        SPANISH: "Saldo: {credits} créditos",
    },
}
