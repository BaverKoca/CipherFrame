"""Route aggregation for the Cipher Frame API."""

from backend.routes.auth_routes import router as auth_router
from backend.routes.admin_routes import router as admin_router
from backend.routes.crypto_routes import router as crypto_router
from backend.routes.image_message_routes import router as image_message_router
from backend.routes.health import router as health_router

__all__ = ["admin_router", "auth_router", "crypto_router", "health_router", "image_message_router"]
