"""FastAPI application for WhatsApp webhook."""

import logging

import uvicorn
from fastapi import FastAPI

from src.config import settings
from src.whatsapp.client import init_whatsapp_client
from src.whatsapp.handlers import register_handlers

logger = logging.getLogger(__name__)


def create_fastapi_app() -> FastAPI:
    """Create FastAPI application with WhatsApp webhook."""
    app = FastAPI(title="Evlampiy Bot API")

    wa = init_whatsapp_client(app)
    if wa:
        register_handlers(wa)
        logger.info("WhatsApp webhook configured")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


async def serve_fastapi() -> None:
    """Serve FastAPI inside the current asyncio loop."""
    app = create_fastapi_app()
    config = uvicorn.Config(
        app,
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    await server.serve()
