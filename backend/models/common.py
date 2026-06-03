"""Shared model helpers for Cipher Frame ORM classes."""

from datetime import datetime, timezone
from enum import Enum as PyEnum


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


def enum_values(enum_cls: type[PyEnum]) -> list[str]:
    """Return the string values for a Python enum class."""

    return [member.value for member in enum_cls]