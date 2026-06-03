"""Server log model for operational observability in Cipher Frame."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.common import utc_now


class LogLevel(str, PyEnum):
    """Supported logging levels stored in the database."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ServerLog(Base):
    """Persistent audit-style log entry for backend events."""

    __tablename__ = "server_logs"
    __table_args__ = (
        Index("ix_server_logs_created_at", "created_at"),
        Index("ix_server_logs_actor_user_id", "actor_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level: Mapped[LogLevel] = mapped_column(
        SQLEnum(
            LogLevel,
            name="log_level",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            create_constraint=True,
        ),
        default=LogLevel.INFO,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    actor = relationship("User", back_populates="server_logs")