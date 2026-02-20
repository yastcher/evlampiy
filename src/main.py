import asyncio
import logging
import threading

from src.config import settings
from src.mongo import init_beanie_models
from src.telegram.setup import build_application
from src.whatsapp.app import run_fastapi_server

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
    "pymongo",
    "uvicorn.access",
)
for logger_name in trash_loggers:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():
    if not settings.telegram_bot_token:
        raise ValueError("need TELEGRAM_BOT_TOKEN env variables")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_beanie_models())

    if settings.whatsapp_token and settings.whatsapp_phone_id:
        api_thread = threading.Thread(target=run_fastapi_server, daemon=True)
        api_thread.start()
        logger.info("FastAPI server started for WhatsApp webhook")

    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        logger.exception("Error: %s", exc)
