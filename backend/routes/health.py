"""Health check route for Cipher Frame."""

from fastapi import APIRouter

from backend.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Application health check")
async def health_check() -> dict[str, str]:
    """Return a simple health response for monitoring and uptime checks."""

    settings = get_settings()
    return {"status": "ok", "application": settings.app_name}
