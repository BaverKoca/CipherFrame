"""Professional SQLite database layer for Cipher Frame."""

from collections.abc import Generator
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


def get_project_root() -> Path:
    """Return the project root directory."""

    return Path(__file__).resolve().parent.parent


def resolve_database_path() -> Path:
    """Resolve the SQLite database path relative to the project root."""

    settings = get_settings()
    database_path = Path(settings.database_path)
    if database_path.is_absolute():
        return database_path
    return (get_project_root() / database_path).resolve()


def get_database_url() -> str:
    """Build the SQLAlchemy database URL for SQLite."""

    return f"sqlite:///{resolve_database_path().as_posix()}"


@lru_cache(maxsize=1)
def get_engine():
    """Create and cache the SQLAlchemy engine."""

    database_path = resolve_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        get_database_url(),
        connect_args={"check_same_thread": False},
    )


@lru_cache(maxsize=1)
def get_session_maker():
    """Create and cache the SQLAlchemy session factory."""

    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependencies."""

    db = get_session_maker()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Import models and create all database tables if they do not exist."""

    from backend.models import admin_action, image_message, rsa_key, server_log, user  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
