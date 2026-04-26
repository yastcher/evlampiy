import asyncio
import logging
import threading

from src.config import settings
from src.mongo import init_beanie_models
from src.telegram.setup import run_bot
from src.whatsapp.app import run_fastapi_server

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if settings.debug else logging.INFO,
)
trash_loggers = (
    "httpcore",
    "httpx",
    "aiogram.event",
    "aiogram.dispatcher",
    "pydub.converter",
    "urllib3",
    "pymongo",
    "uvicorn.access",
)
for logger_name in trash_loggers:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def _async_main() -> None:
    await init_beanie_models()

    if settings.whatsapp_token and settings.whatsapp_phone_id:
        api_thread = threading.Thread(target=run_fastapi_server, daemon=True)
        api_thread.start()
        logger.info("FastAPI server started for WhatsApp webhook")

    await run_bot()


def main() -> None:
    if not settings.telegram_bot_token:
        raise ValueError("need TELEGRAM_BOT_TOKEN env variables")
    asyncio.run(_async_main())


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        logger.exception("Error: %s", exc)
