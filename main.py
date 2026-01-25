import asyncio
import logging

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.config import settings
from src.gpt_commands import evlampiy_command
from src.mongo import init_beanie_models
from src.telegram import handlers
from src.telegram.bot import application
from src.telegram.voice import from_voice_to_text

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if settings.debug else logging.INFO,
)
trash_loggers = (
    "httpcore",
    "httpx",
    "telegram.ext.ExtBot",
    "pydub.converter",
    "urllib3",
    "pymongo.topology",
)
for logger_name in trash_loggers:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

COMMAND_HANDLERS = {
    "start": handlers.start,
    "choose_your_language": handlers.choose_language,
    "enter_your_command": handlers.enter_your_command,
    "evlampiy": evlampiy_command,
}


if not settings.telegram_bot_token:
    raise ValueError("need TELEGRAM_BOT_TOKEN env variables")


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_beanie_models())

    for command_name, command_handler in COMMAND_HANDLERS.items():
        application.add_handler(CommandHandler(command_name, command_handler))

    application.add_handler(
        CallbackQueryHandler(handlers.lang_buttons, pattern="set_lang_")
    )

    application.add_handler(MessageHandler(filters.VOICE, from_voice_to_text))

    enter_command_handler = ConversationHandler(
        entry_points=[
            CommandHandler("enter_your_command", handlers.enter_your_command)
        ],
        states={
            handlers.WAITING_FOR_COMMAND: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handlers.handle_command_input
                )
            ]
        },
        fallbacks=[],
    )
    application.add_handler(enter_command_handler)

    application.run_polling()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        logger.exception("Error: %s", exc)
