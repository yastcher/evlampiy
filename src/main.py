import asyncio
import logging

from src.config import settings
from src.mongo import init_beanie_models
from src.telegram.setup import run_bot
from src.whatsapp.app import serve_fastapi

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

    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(run_bot())
        # Always serve the HTTP app: /health must answer liveness probes even when
        # WhatsApp is unconfigured (its webhook routes are registered conditionally).
        task_group.create_task(serve_fastapi())


def main() -> None:
    if not settings.telegram_bot_token:
        raise ValueError("need TELEGRAM_BOT_TOKEN env variables")
    asyncio.run(_async_main())


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        logger.exception("Error: %s", exc)
