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
            "I can translate a voice message to text!\n"
            "current language are: {chat_language}\n"
            "current voice command are (you can start voice from): {gpt_command}\n"
            "/start - Show this message\n"
            "/choose_your_language - Set the voice language"
        ),
        GERMANY: (
            "Ich kann eine Sprachnachricht in Text übersetzen!\n"
            "Aktuelle Sprache: {chat_language}\n"
            "Aktueller Sprachbefehl ist (Sie können die Spracherkennung starten mit): {gpt_command}\n"
            "/start - Zeige diese Nachricht\n"
            "/choose_your_language - Legen Sie die Sprache fest"
        ),
        RUSSIAN: (
            "Я могу перевести голосовое сообщение в текст!\n"
            "Текущий язык: {chat_language}\n"
            "Текущая голосовая команда (вы можете начать голос с): {gpt_command}\n"
            "/start - Показать это сообщение\n"
            "/choose_your_language - Установить язык голосовых сообщений"
        ),
        SPANISH: (
            "¡Puedo traducir un mensaje de voz a texto!\n"
            "El idioma actual es: {chat_language}\n"
            "El comando de voz actual es (puedes iniciar la voz desde): {gpt_command}\n"
            "/start - Muestra este mensaje\n"
            "/choose_your_language - Configura el idioma de voz"
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
}
