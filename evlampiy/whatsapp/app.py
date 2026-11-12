"""FastAPI application for WhatsApp webhook."""

import logging

import uvicorn
from fastapi import FastAPI

from evlampiy.config import settings
from evlampiy.whatsapp.client import init_whatsapp_client, whatsapp_state
from evlampiy.whatsapp.handlers import register_handlers

logger = logging.getLogger(__name__)


def create_fastapi_app() -> FastAPI:
    """Create FastAPI application with WhatsApp webhook."""
    # No /docs, /redoc or /openapi.json: nothing in the bot reads them, and the proxy in
    # docs/DEPLOY.md passes `/` through, so they would map the API for anyone.
    app = FastAPI(title="Evlampiy Bot API", docs_url=None, redoc_url=None, openapi_url=None)

    wa = init_whatsapp_client(app)
    if wa:
        register_handlers(wa)
        logger.info("WhatsApp webhook configured")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "whatsapp": whatsapp_state()}

    return app


async def serve_fastapi() -> None:
    """Serve the HTTP app (always-on /health, plus the WhatsApp webhook when configured)."""
    app = create_fastapi_app()
    config = uvicorn.Config(
        app,
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    logger.info(
        "HTTP server listening on %s:%s (/health always on)",
        settings.fastapi_host,
        settings.fastapi_port,
    )
    await server.serve()
