"""Logging configuration for Cipher Frame."""

import logging
from logging.config import dictConfig

from backend.config import get_settings


def configure_logging() -> None:
    """Configure application logging once during startup."""

    settings = get_settings()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": settings.log_level,
                },
            },
            "root": {
                "handlers": ["console"],
                "level": settings.log_level,
            },
        }
    )
    logging.getLogger(__name__).debug("Logging configured for %s", settings.app_name)
