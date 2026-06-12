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
        ENGLISH: "Not enough tokens. Use /buy to purchase more.",
        GERMAN: "Nicht genügend Tokens. Verwenden Sie /buy, um mehr zu kaufen.",
        RUSSIAN: "Недостаточно токенов. Используйте /buy для покупки.",
        SPANISH: "No tienes suficientes tokens. Usa /buy para comprar más.",
    },
    "blocked_message": {
        ENGLISH: "You are blocked from using this bot.",
        GERMAN: "Sie sind für die Nutzung dieses Bots gesperrt.",
        RUSSIAN: "Вы заблокированы и не можете использовать бота.",
        SPANISH: "Estás bloqueado y no puedes usar este bot.",
    },
    "credits_exhausted_warning": {
        ENGLISH: (
            "Your token balance is exhausted. The transcription was still processed. Use /buy to purchase more tokens."
        ),
        GERMAN: (
            "Ihr Token-Guthaben ist erschöpft. "
            "Die Transkription wurde trotzdem verarbeitet. Verwenden Sie /buy für mehr Tokens."
        ),
        RUSSIAN: (
            "Ваш баланс токенов исчерпан. Транскрипция всё равно была обработана. Используйте /buy для покупки токенов."
        ),
        SPANISH: (
            "Tu saldo de tokens se ha agotado. "
            "La transcripción se procesó de todos modos. Usa /buy para comprar más tokens."
        ),
    },
    "buy_packages_prompt": {
        ENGLISH: "Choose a token package:",
        GERMAN: "Wählen Sie ein Token-Paket:",
        RUSSIAN: "Выберите пакет токенов:",
        SPANISH: "Elige un paquete de tokens:",
    },
    "service_unavailable": {
        ENGLISH: "Transcription service is temporarily unavailable. Please try again later.",
        GERMAN: ("Transkriptionsdienst ist vorübergehend nicht verfügbar. Bitte versuchen Sie es später erneut."),
        RUSSIAN: "Сервис транскрипции временно недоступен. Попробуйте позже.",
        SPANISH: ("El servicio de transcripción no está disponible temporalmente. Inténtalo más tarde."),
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
    "cleanup_enabled": {
        ENGLISH: "Text cleanup enabled \u2728",
        GERMAN: "Textbereinigung aktiviert \u2728",
        RUSSIAN: "Очистка текста включена \u2728",
        SPANISH: "Limpieza de texto activada \u2728",
    },
    "cleanup_disabled": {
        ENGLISH: "Text cleanup disabled.",
        GERMAN: "Textbereinigung deaktiviert.",
        RUSSIAN: "Очистка текста выключена.",
        SPANISH: "Limpieza de texto desactivada.",
    },
    "categorize_done": {
        ENGLISH: "Categorized {count} notes.",
        GERMAN: "{count} Notizen kategorisiert.",
        RUSSIAN: "Категоризировано заметок: {count}.",
        SPANISH: "{count} notas categorizadas.",
    },
    "categorize_no_files": {
        ENGLISH: "No files to categorize in inbox folder.",
        GERMAN: "Keine Dateien zum Kategorisieren im Eingangsordner.",
        RUSSIAN: "Нет файлов для категоризации в папке inbox.",
        SPANISH: "No hay archivos para categorizar en la carpeta de entrada.",
    },
    "mystats_message": {
        ENGLISH: (
            "📊 <b>Your Statistics</b>\n\n"
            "Balance: {credits} tokens\n"
            "Tier: {tier}\n\n"
            "<b>All time:</b>\n"
            "• Transcriptions: {total_transcriptions}\n"
            "• Tokens used: {total_tokens_used}\n"
            "• Tokens purchased: {total_purchased}"
        ),
        GERMAN: (
            "📊 <b>Ihre Statistiken</b>\n\n"
            "Guthaben: {credits} Tokens\n"
            "Stufe: {tier}\n\n"
            "<b>Insgesamt:</b>\n"
            "• Transkriptionen: {total_transcriptions}\n"
            "• Tokens verbraucht: {total_tokens_used}\n"
            "• Tokens gekauft: {total_purchased}"
        ),
        RUSSIAN: (
            "📊 <b>Ваша статистика</b>\n\n"
            "Баланс: {credits} токенов\n"
            "Тариф: {tier}\n\n"
            "<b>За всё время:</b>\n"
            "• Транскрипций: {total_transcriptions}\n"
            "• Потрачено токенов: {total_tokens_used}\n"
            "• Куплено токенов: {total_purchased}"
        ),
        SPANISH: (
            "📊 <b>Tus estadísticas</b>\n\n"
            "Saldo: {credits} tokens\n"
            "Nivel: {tier}\n\n"
            "<b>Total:</b>\n"
            "• Transcripciones: {total_transcriptions}\n"
            "• Tokens usados: {total_tokens_used}\n"
            "• Tokens comprados: {total_purchased}"
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
    "obsidian_hub_connected": {
        ENGLISH: (
            "📝 <b>Notes</b> — <code>{owner}/{repo}</code>\n\n"
            "<b>First-time setup:</b>\n"
            "1. Install <b>obsidian-git</b> community plugin\n"
            "2. Clone as a new vault:\n"
            "   <code>https://github.com/{owner}/{repo}</code>\n"
            "3. Enable auto-pull in plugin settings\n"
            "4. New notes appear in <code>{inbox_dir}/</code>\n\n"
            "Open vault (tap to copy, paste in browser):\n"
            "<code>obsidian://open?vault={repo}</code>\n\n"
            "Use <b>Setup Obsidian</b> below to pre-configure obsidian-git in the repo."
        ),
        GERMAN: (
            "📝 <b>Notizen</b> — <code>{owner}/{repo}</code>\n\n"
            "<b>Ersteinrichtung:</b>\n"
            "1. Community-Plugin <b>obsidian-git</b> installieren\n"
            "2. Als neues Vault klonen:\n"
            "   <code>https://github.com/{owner}/{repo}</code>\n"
            "3. Repo als Vault öffnen — Plugin ist bereits konfiguriert\n"
            "4. Neue Notizen erscheinen in <code>{inbox_dir}/</code>\n\n"
            "Vault öffnen (tippen zum Kopieren, im Browser einfügen):\n"
            "<code>obsidian://open?vault={repo}</code>\n\n"
            "<b>Obsidian einrichten</b> unten konfiguriert obsidian-git automatisch."
        ),
        RUSSIAN: (
            "📝 <b>Заметки</b> — <code>{owner}/{repo}</code>\n\n"
            "<b>Первоначальная настройка:</b>\n"
            "1. Установить community-плагин <b>obsidian-git</b>\n"
            "2. Клонировать как новый vault:\n"
            "   <code>https://github.com/{owner}/{repo}</code>\n"
            "3. Открыть как vault — плагин уже настроен\n"
            "4. Новые заметки в папке <code>{inbox_dir}/</code>\n\n"
            "Открыть vault (нажми для копирования, вставь в браузер):\n"
            "<code>obsidian://open?vault={repo}</code>\n\n"
            "Кнопка <b>Настроить Obsidian</b> создаёт конфиг плагина в репозитории."
        ),
        SPANISH: (
            "📝 <b>Notas</b> — <code>{owner}/{repo}</code>\n\n"
            "<b>Configuración inicial:</b>\n"
            "1. Instalar plugin comunitario <b>obsidian-git</b>\n"
            "2. Clonar como nuevo vault:\n"
            "   <code>https://github.com/{owner}/{repo}</code>\n"
            "3. Abrir como vault — el plugin ya está configurado\n"
            "4. Las nuevas notas aparecen en <code>{inbox_dir}/</code>\n\n"
            "Abrir vault (toca para copiar, pega en el navegador):\n"
            "<code>obsidian://open?vault={repo}</code>\n\n"
            "El botón <b>Configurar Obsidian</b> crea el config del plugin en el repo."
        ),
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
    "btn_provider": {
        ENGLISH: "🔊 Provider",
        GERMAN: "🔊 Anbieter",
        RUSSIAN: "🔊 Провайдер",
        SPANISH: "🔊 Proveedor",
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
    "btn_toggle_cleanup_on": {
        ENGLISH: "\u2728 Text cleanup: ON",
        GERMAN: "\u2728 Textbereinigung: AN",
        RUSSIAN: "\u2728 Очистка текста: ВКЛ",
        SPANISH: "\u2728 Limpieza de texto: S\u00cd",
    },
    "btn_toggle_cleanup_off": {
        ENGLISH: "Text cleanup: OFF",
        GERMAN: "Textbereinigung: AUS",
        RUSSIAN: "Очистка текста: ВЫКЛ",
        SPANISH: "Limpieza de texto: NO",
    },
    "btn_categorize_all": {
        ENGLISH: "📂 Categorize all",
        GERMAN: "📂 Alle kategorisieren",
        RUSSIAN: "📂 Категоризировать всё",
        SPANISH: "📂 Categorizar todo",
    },
    "btn_setup_obsidian_git": {
        ENGLISH: "⚙️ Setup Obsidian",
        GERMAN: "⚙️ Obsidian einrichten",
        RUSSIAN: "⚙️ Настроить Obsidian",
        SPANISH: "⚙️ Configurar Obsidian",
    },
    "obsidian_git_setup_done": {
        ENGLISH: ("Config created! Clone the repo, open as vault, enable obsidian-git — done."),
        GERMAN: ("Konfiguration erstellt! Repo klonen, als Vault öffnen, obsidian-git aktivieren — fertig."),
        RUSSIAN: ("Конфиг создан! Клонируй репо, открой как vault, включи obsidian-git — готово."),
        SPANISH: ("¡Configuración creada! Clona el repo, ábrelo como vault, activa obsidian-git — listo."),
    },
    "obsidian_git_setup_failed": {
        ENGLISH: "Failed to create config. Check GitHub connection.",
        GERMAN: "Konfiguration fehlgeschlagen. GitHub-Verbindung prüfen.",
        RUSSIAN: "Не удалось создать конфиг. Проверь подключение к GitHub.",
        SPANISH: "Error al crear la configuración. Verifica la conexión de GitHub.",
    },
    "btn_disconnect_github": {
        ENGLISH: "❌ Disconnect GitHub",
        GERMAN: "❌ GitHub trennen",
        RUSSIAN: "❌ Отключить GitHub",
        SPANISH: "❌ Desconectar GitHub",
    },
    "btn_buy": {
        ENGLISH: "💳 Buy tokens",
        GERMAN: "💳 Tokens kaufen",
        RUSSIAN: "💳 Купить токены",
        SPANISH: "💳 Comprar tokens",
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
    "choose_provider_prompt": {
        ENGLISH: "Choose transcription provider:",
        GERMAN: "Transkriptionsanbieter wählen:",
        RUSSIAN: "Выберите провайдер транскрипции:",
        SPANISH: "Elige el proveedor de transcripción:",
    },
    "choose_my_provider_auto": {
        ENGLISH: "Provider: Auto",
        GERMAN: "Anbieter: Auto",
        RUSSIAN: "Провайдер: Авто",
        SPANISH: "Proveedor: Auto",
    },
    "choose_my_provider_wit": {
        ENGLISH: "Provider: Wit.ai",
        GERMAN: "Anbieter: Wit.ai",
        RUSSIAN: "Провайдер: Wit.ai",
        SPANISH: "Proveedor: Wit.ai",
    },
    "choose_my_provider_groq": {
        ENGLISH: "Provider: Groq",
        GERMAN: "Anbieter: Groq",
        RUSSIAN: "Провайдер: Groq",
        SPANISH: "Proveedor: Groq",
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
        ENGLISH: ("GitHub authorization failed or timed out. Try /connect_github again."),
        GERMAN: ("GitHub-Autorisierung fehlgeschlagen oder abgelaufen. Versuchen Sie /connect_github erneut."),
        RUSSIAN: ("Авторизация GitHub не удалась или истекло время. Попробуйте /connect_github снова."),
        SPANISH: ("Autorización de GitHub fallida o expirada. Intenta /connect_github de nuevo."),
    },
    "github_repo_failed": {
        ENGLISH: "Failed to create/access GitHub repository.",
        GERMAN: "GitHub-Repository konnte nicht erstellt/zugegriffen werden.",
        RUSSIAN: "Не удалось создать/получить доступ к репозиторию GitHub.",
        SPANISH: "Error al crear/acceder al repositorio de GitHub.",
    },
    "github_connected": {
        ENGLISH: ("GitHub connected! Repository: {owner}/{repo}\nObsidian sync is now enabled."),
        GERMAN: ("GitHub verbunden! Repository: {owner}/{repo}\nObsidian-Sync ist jetzt aktiviert."),
        RUSSIAN: ("GitHub подключён! Репозиторий: {owner}/{repo}\nСинхронизация с Obsidian включена."),
        SPANISH: ("¡GitHub conectado! Repositorio: {owner}/{repo}\nSincronización con Obsidian activada."),
    },
    "whatsapp_link_prompt": {
        ENGLISH: ("Send this message to the bot on WhatsApp:\n\nlink {code}\n\nCode expires in 5 minutes."),
        GERMAN: ("Senden Sie diese Nachricht an den Bot auf WhatsApp:\n\nlink {code}\n\nCode läuft in 5 Minuten ab."),
        RUSSIAN: ("Отправьте это сообщение боту в WhatsApp:\n\nlink {code}\n\nКод действителен 5 минут."),
        SPANISH: ("Envía este mensaje al bot en WhatsApp:\n\nlink {code}\n\nEl código expira en 5 minutos."),
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
    "balance_detailed": {
        ENGLISH: (
            "🎫 Balance: {total} tokens\n"
            "├ Free: {free}/{free_max} (monthly)\n"
            "└ Purchased: {purchased}\n\n"
            "📊 This month:\n"
            "├ Transcriptions: {month_transcriptions}\n"
            "├ Audio: {month_audio}\n"
            "└ Tokens used: {month_tokens}\n\n"
            "💡 1 token = 20 sec audio"
        ),
        GERMAN: (
            "🎫 Guthaben: {total} Tokens\n"
            "├ Kostenlos: {free}/{free_max} (monatlich)\n"
            "└ Gekauft: {purchased}\n\n"
            "📊 Dieser Monat:\n"
            "├ Transkriptionen: {month_transcriptions}\n"
            "├ Audio: {month_audio}\n"
            "└ Tokens verbraucht: {month_tokens}\n\n"
            "💡 1 Token = 20 Sek. Audio"
        ),
        RUSSIAN: (
            "🎫 Баланс: {total} токенов\n"
            "├ Бесплатных: {free}/{free_max} (ежемесячно)\n"
            "└ Купленных: {purchased}\n\n"
            "📊 Этот месяц:\n"
            "├ Транскрипций: {month_transcriptions}\n"
            "├ Аудио: {month_audio}\n"
            "└ Токенов использовано: {month_tokens}\n\n"
            "💡 1 токен = 20 сек аудио"
        ),
        SPANISH: (
            "🎫 Saldo: {total} tokens\n"
            "├ Gratis: {free}/{free_max} (mensual)\n"
            "└ Comprados: {purchased}\n\n"
            "📊 Este mes:\n"
            "├ Transcripciones: {month_transcriptions}\n"
            "├ Audio: {month_audio}\n"
            "└ Tokens usados: {month_tokens}\n\n"
            "💡 1 token = 20 seg de audio"
        ),
    },
    # Admin interface
    "admin_hub_title": {
        ENGLISH: "🔧 Admin Panel",
        GERMAN: "🔧 Admin-Panel",
        RUSSIAN: "🔧 Панель администратора",
        SPANISH: "🔧 Panel de administración",
    },
    "btn_manage_vip": {
        ENGLISH: "⭐ VIP users",
        GERMAN: "⭐ VIP-Benutzer",
        RUSSIAN: "⭐ VIP пользователи",
        SPANISH: "⭐ Usuarios VIP",
    },
    "btn_manage_testers": {
        ENGLISH: "🧪 Testers",
        GERMAN: "🧪 Tester",
        RUSSIAN: "🧪 Тестеры",
        SPANISH: "🧪 Testers",
    },
    "btn_manage_blocked": {
        ENGLISH: "🚫 Blocked users",
        GERMAN: "🚫 Gesperrte Benutzer",
        RUSSIAN: "🚫 Заблокированные",
        SPANISH: "🚫 Usuarios bloqueados",
    },
    "btn_admin_stats": {
        ENGLISH: "📊 Stats",
        GERMAN: "📊 Statistiken",
        RUSSIAN: "📊 Статистика",
        SPANISH: "📊 Estadísticas",
    },
    "btn_add_credits": {
        ENGLISH: "💰 Add credits",
        GERMAN: "💰 Credits hinzufügen",
        RUSSIAN: "💰 Начислить кредиты",
        SPANISH: "💰 Añadir créditos",
    },
    "admin_vip_list": {
        ENGLISH: ("<b>VIP users:</b>\n{users}\n\nUse /add_vip &lt;user_id&gt; or /remove_vip &lt;user_id&gt;"),
        GERMAN: ("<b>VIP-Benutzer:</b>\n{users}\n\nVerwende /add_vip &lt;user_id&gt; oder /remove_vip &lt;user_id&gt;"),
        RUSSIAN: (
            "<b>VIP пользователи:</b>\n{users}\n\nИспользуйте /add_vip &lt;user_id&gt; или /remove_vip &lt;user_id&gt;"
        ),
        SPANISH: ("<b>Usuarios VIP:</b>\n{users}\n\nUsa /add_vip &lt;user_id&gt; o /remove_vip &lt;user_id&gt;"),
    },
    "admin_tester_list": {
        ENGLISH: ("<b>Testers:</b>\n{users}\n\nUse /add_tester &lt;user_id&gt; or /remove_tester &lt;user_id&gt;"),
        GERMAN: ("<b>Tester:</b>\n{users}\n\nVerwende /add_tester &lt;user_id&gt; oder /remove_tester &lt;user_id&gt;"),
        RUSSIAN: (
            "<b>Тестеры:</b>\n{users}\n\nИспользуйте /add_tester &lt;user_id&gt; или /remove_tester &lt;user_id&gt;"
        ),
        SPANISH: ("<b>Testers:</b>\n{users}\n\nUsa /add_tester &lt;user_id&gt; o /remove_tester &lt;user_id&gt;"),
    },
    "admin_blocked_list": {
        ENGLISH: ("<b>Blocked users:</b>\n{users}\n\nUse /block &lt;user_id&gt; or /unblock &lt;user_id&gt;"),
        GERMAN: (
            "<b>Gesperrte Benutzer:</b>\n{users}\n\nVerwende /block &lt;user_id&gt; oder /unblock &lt;user_id&gt;"
        ),
        RUSSIAN: (
            "<b>Заблокированные:</b>\n{users}\n\nИспользуйте /block &lt;user_id&gt; или /unblock &lt;user_id&gt;"
        ),
        SPANISH: ("<b>Usuarios bloqueados:</b>\n{users}\n\nUsa /block &lt;user_id&gt; o /unblock &lt;user_id&gt;"),
    },
    "admin_user_blocked": {
        ENGLISH: "User {user_id} has been blocked.",
        GERMAN: "Benutzer {user_id} wurde gesperrt.",
        RUSSIAN: "Пользователь {user_id} заблокирован.",
        SPANISH: "Usuario {user_id} ha sido bloqueado.",
    },
    "admin_user_unblocked": {
        ENGLISH: "User {user_id} has been unblocked.",
        GERMAN: "Benutzer {user_id} wurde entsperrt.",
        RUSSIAN: "Пользователь {user_id} разблокирован.",
        SPANISH: "Usuario {user_id} ha sido desbloqueado.",
    },
    "admin_list_empty": {
        ENGLISH: "(empty)",
        GERMAN: "(leer)",
        RUSSIAN: "(пусто)",
        SPANISH: "(vacío)",
    },
    "admin_user_added": {
        ENGLISH: "User {user_id} added as {role}.",
        GERMAN: "Benutzer {user_id} als {role} hinzugefügt.",
        RUSSIAN: "Пользователь {user_id} добавлен как {role}.",
        SPANISH: "Usuario {user_id} añadido como {role}.",
    },
    "admin_user_removed": {
        ENGLISH: "User {user_id} removed from {role}.",
        GERMAN: "Benutzer {user_id} aus {role} entfernt.",
        RUSSIAN: "Пользователь {user_id} удалён из {role}.",
        SPANISH: "Usuario {user_id} eliminado de {role}.",
    },
    "admin_user_not_found": {
        ENGLISH: "User {user_id} not found in {role} list.",
        GERMAN: "Benutzer {user_id} nicht in {role}-Liste gefunden.",
        RUSSIAN: "Пользователь {user_id} не найден в списке {role}.",
        SPANISH: "Usuario {user_id} no encontrado en la lista de {role}.",
    },
    "admin_credits_added": {
        ENGLISH: "Added {amount} credits to user {user_id}. New balance: {balance}.",
        GERMAN: "{amount} Credits zu Benutzer {user_id} hinzugefügt. Neues Guthaben: {balance}.",
        RUSSIAN: "Начислено {amount} кредитов пользователю {user_id}. Баланс: {balance}.",
        SPANISH: "{amount} créditos añadidos al usuario {user_id}. Nuevo saldo: {balance}.",
    },
    "admin_usage": {
        ENGLISH: "Usage: {command}",
        GERMAN: "Verwendung: {command}",
        RUSSIAN: "Использование: {command}",
        SPANISH: "Uso: {command}",
    },
}
