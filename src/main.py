import asyncio
import logging
import typing

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

_SUPERVISOR_INITIAL_BACKOFF_SECONDS = 1.0
_SUPERVISOR_MAX_BACKOFF_SECONDS = 60.0


async def _supervise(name: str, factory: typing.Callable[[], typing.Awaitable[None]]) -> None:
    """Keep a subsystem running: restart it on crash with exponential backoff.

    Telegram polling and the HTTP server are independent — one crashing must not tear the
    other down (a plain TaskGroup would cancel the siblings and kill the process). A clean
    return is not restarted; cancellation propagates for an orderly shutdown.
    """
    backoff = _SUPERVISOR_INITIAL_BACKOFF_SECONDS
    while True:
        try:
            await factory()
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Subsystem %s crashed; restarting in %.0fs", name, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _SUPERVISOR_MAX_BACKOFF_SECONDS)


async def _async_main() -> None:
    await init_beanie_models()

    # Each subsystem is supervised independently so one failing surface (Telegram or the
    # HTTP/WhatsApp server) restarts on its own instead of taking the whole process down.
    async with asyncio.TaskGroup() as task_group:
        task_group.create_task(_supervise("telegram", run_bot))
        task_group.create_task(_supervise("http", serve_fastapi))


def main() -> None:
    if not settings.telegram_bot_token:
        raise ValueError("need TELEGRAM_BOT_TOKEN env variables")
    asyncio.run(_async_main())


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        logger.exception("Error: %s", exc)
