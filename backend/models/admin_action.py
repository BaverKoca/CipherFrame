"""Admin action model for auditability in Cipher Frame."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.common import utc_now


class AdminAction(Base):
    """Records privileged admin actions for accountability."""

    __tablename__ = "admin_actions"
    __table_args__ = (
        Index("ix_admin_actions_created_at", "created_at"),
        Index("ix_admin_actions_admin_user_id", "admin_user_id"),
        Index("ix_admin_actions_target_user_id", "target_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    admin_user = relationship("User", foreign_keys=[admin_user_id], back_populates="admin_actions_created")
    target_user = relationship("User", foreign_keys=[target_user_id], back_populates="admin_actions_targeted")