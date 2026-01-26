import asyncio
import logging
import threading

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from src.config import settings
from src.gpt_commands import evlampiy_command
from src.mongo import init_beanie_models
from src.telegram import handlers
from src.telegram.payments import (
    balance_command,
    buy_command,
    handle_pre_checkout,
    handle_successful_payment,
)
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
    "uvicorn.access",
)
for logger_name in trash_loggers:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

COMMAND_HANDLERS = {
    "start": handlers.start,
    "choose_your_language": handlers.choose_language,
    "enter_your_command": handlers.enter_your_command,
    "evlampiy": evlampiy_command,
    "connect_github": handlers.connect_github,
    "toggle_obsidian": handlers.toggle_obsidian,
    "disconnect_github": handlers.disconnect_github,
    "buy": buy_command,
    "balance": balance_command,
}


def create_fastapi_app():
    """Create FastAPI application with WhatsApp webhook."""
    from fastapi import FastAPI

    from src.whatsapp.client import get_whatsapp_client
    from src.whatsapp.handlers import register_handlers

    app = FastAPI(title="Evlampiy Bot API")

    wa = get_whatsapp_client()
    if wa:
        register_handlers(wa)
        wa.setup_fastapi(app)
        logger.info("WhatsApp webhook configured")

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app


def run_fastapi_server():
    """Run FastAPI server in a separate thread."""
    import uvicorn

    app = create_fastapi_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


def main():
    if not settings.telegram_bot_token:
        raise ValueError("need TELEGRAM_BOT_TOKEN env variables")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_beanie_models())

    # Start FastAPI server if WhatsApp is configured
    if settings.whatsapp_token and settings.whatsapp_phone_id:
        api_thread = threading.Thread(target=run_fastapi_server, daemon=True)
        api_thread.start()
        logger.info("FastAPI server started for WhatsApp webhook")

    application = ApplicationBuilder().token(settings.telegram_bot_token).build()

    for command_name, command_handler in COMMAND_HANDLERS.items():
        application.add_handler(CommandHandler(command_name, command_handler))

    application.add_handler(CallbackQueryHandler(handlers.lang_buttons, pattern="set_lang_"))

    application.add_handler(MessageHandler(filters.VOICE, from_voice_to_text))

    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment)
    )

    enter_command_handler = ConversationHandler(
        entry_points=[CommandHandler("enter_your_command", handlers.enter_your_command)],
        states={
            handlers.WAITING_FOR_COMMAND: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_command_input)
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
