"""FastAPI application for WhatsApp webhook."""

import logging

import uvicorn
from fastapi import FastAPI

from src.config import settings
from src.whatsapp.client import get_whatsapp_client
from src.whatsapp.handlers import register_handlers

logger = logging.getLogger(__name__)


def create_fastapi_app() -> FastAPI:
    """Create FastAPI application with WhatsApp webhook."""
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


def run_fastapi_server() -> None:
    """Run FastAPI server in a separate thread."""
    app = create_fastapi_app()
    uvicorn.run(
        app,
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        log_level="warning",
    )
