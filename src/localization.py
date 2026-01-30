from src.config import ENGLISH, GERMANY, RUSSIAN, SPANISH

translates = {
    "success": {
        ENGLISH: "Success",
        GERMANY: "Erfolg",
        RUSSIAN: "Успешно",
        SPANISH: "Éxito",
    },
    "not_found": {
        ENGLISH: "Not found",
        GERMANY: "Nicht gefunden",
        RUSSIAN: "Не найден",
        SPANISH: "No encontrado",
    },
    "error_connection": {
        ENGLISH: "Connection error. Try later",
        GERMANY: "Verbindungsfehler. Versuchen Sie es später",
        RUSSIAN: "Ошибка соединения. Попробуйте позднее",
        SPANISH: "Error de conexión. Inténtalo más tarde",
    },
    "bad_data": {
        ENGLISH: "Bad data",
        GERMANY: "Schlechte Daten",
        RUSSIAN: "Неверные данные",
        SPANISH: "Datos incorrectos",
    },
    "choose_my_language": {
        ENGLISH: "Selected language: English",
        GERMANY: "Ausgewählte Sprache: Deutsch",
        RUSSIAN: "Выбранный язык: Русский",
        SPANISH: "Idioma seleccionado: Español",
    },
    "start_message": {
        ENGLISH: (
            "Voice-to-text bot. Just send a voice message!\n\n"
            "Language: {chat_language}\n"
            "GPT trigger: {gpt_command}\n\n"
            "Commands:\n"
            "/choose_your_language - Change language\n"
            "/buy - Buy credits\n"
            "/balance - Check balance\n"
            "/mystats - Your statistics"
        ),
        GERMANY: (
            "Sprache-zu-Text Bot. Sende einfach eine Sprachnachricht!\n\n"
            "Sprache: {chat_language}\n"
            "GPT-Trigger: {gpt_command}\n\n"
            "Befehle:\n"
            "/choose_your_language - Sprache ändern\n"
            "/buy - Credits kaufen\n"
            "/balance - Guthaben prüfen\n"
            "/mystats - Deine Statistiken"
        ),
        RUSSIAN: (
            "Бот для транскрипции голоса. Просто отправьте голосовое сообщение!\n\n"
            "Язык: {chat_language}\n"
            "Триггер GPT: {gpt_command}\n\n"
            "Команды:\n"
            "/choose_your_language - Сменить язык\n"
            "/buy - Купить кредиты\n"
            "/balance - Проверить баланс\n"
            "/mystats - Ваша статистика"
        ),
        SPANISH: (
            "Bot de voz a texto. ¡Solo envía un mensaje de voz!\n\n"
            "Idioma: {chat_language}\n"
            "Activador GPT: {gpt_command}\n\n"
            "Comandos:\n"
            "/choose_your_language - Cambiar idioma\n"
            "/buy - Comprar créditos\n"
            "/balance - Ver saldo\n"
            "/mystats - Tus estadísticas"
        ),
    },
    "insufficient_credits": {
        ENGLISH: "Not enough credits. Use /buy to purchase more.",
        GERMANY: "Nicht genügend Credits. Verwenden Sie /buy, um mehr zu kaufen.",
        RUSSIAN: "Недостаточно кредитов. Используйте /buy для покупки.",
        SPANISH: "No tienes suficientes créditos. Usa /buy para comprar más.",
    },
    "service_unavailable": {
        ENGLISH: "Transcription service is temporarily unavailable. Please try again later.",
        GERMANY: "Transkriptionsdienst ist vorübergehend nicht verfügbar. Bitte versuchen Sie es später erneut.",
        RUSSIAN: "Сервис транскрипции временно недоступен. Попробуйте позже.",
        SPANISH: "El servicio de transcripción no está disponible temporalmente. Inténtalo más tarde.",
    },
    "categorize_enabled": {
        ENGLISH: "Auto-categorization enabled.",
        GERMANY: "Automatische Kategorisierung aktiviert.",
        RUSSIAN: "Автокатегоризация включена.",
        SPANISH: "Categorización automática activada.",
    },
    "categorize_disabled": {
        ENGLISH: "Auto-categorization disabled.",
        GERMANY: "Automatische Kategorisierung deaktiviert.",
        RUSSIAN: "Автокатегоризация выключена.",
        SPANISH: "Categorización automática desactivada.",
    },
    "categorize_done": {
        ENGLISH: "Categorized {count} notes.",
        GERMANY: "{count} Notizen kategorisiert.",
        RUSSIAN: "Категоризировано заметок: {count}.",
        SPANISH: "{count} notas categorizadas.",
    },
    "categorize_no_files": {
        ENGLISH: "No files to categorize in income folder.",
        GERMANY: "Keine Dateien zum Kategorisieren im Eingangsordner.",
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
        GERMANY: (
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
}
