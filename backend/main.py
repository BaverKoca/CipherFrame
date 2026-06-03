"""FastAPI application entry point for Cipher Frame."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.database import init_db
from backend.logger import configure_logging
from backend.routes import admin_router, auth_router, crypto_router, health_router, image_message_router
from backend.services.seed_service import seed_default_admin
from backend.websocket.websocket_service import register_event_loop, router as websocket_router

settings = get_settings()
logger = logging.getLogger(__name__)


def get_frontend_directory() -> Path:
    """Resolve the frontend directory relative to the project root."""

    return Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup and shutdown hooks for the application lifecycle."""

    configure_logging()
    register_event_loop(asyncio.get_running_loop())
    logger.info("Starting %s", settings.app_name)
    init_db()
    logger.info("Database schema initialized")
    seed_created = seed_default_admin()
    if seed_created:
        logger.info("Default admin user seeded")
    else:
        logger.info("Default admin user already present or not created")
    yield
    register_event_loop(None)
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(crypto_router)
app.include_router(image_message_router)
app.include_router(websocket_router)
app.include_router(health_router)
app.mount("/", StaticFiles(directory=get_frontend_directory(), html=True), name="frontend")
