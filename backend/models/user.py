"""User model for Cipher Frame actors and administrators."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.common import utc_now


class UserRole(str, PyEnum):
    """Roles supported by Cipher Frame."""

    CLIENT = "client"
    ADMIN = "admin"


class User(Base):
    """Application user with client/admin role separation."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            create_constraint=True,
        ),
        default=UserRole.CLIENT,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rsa_keypairs = relationship("RSAKeyPair", back_populates="user", cascade="all, delete-orphan")
    image_messages_sent = relationship(
        "ImageMessage",
        foreign_keys="ImageMessage.sender_id",
        back_populates="sender",
    )
    image_messages_received = relationship(
        "ImageMessage",
        foreign_keys="ImageMessage.receiver_id",
        back_populates="receiver",
    )
    server_logs = relationship("ServerLog", back_populates="actor")
    admin_actions_created = relationship(
        "AdminAction",
        foreign_keys="AdminAction.admin_user_id",
        back_populates="admin_user",
    )
    admin_actions_targeted = relationship(
        "AdminAction",
        foreign_keys="AdminAction.target_user_id",
        back_populates="target_user",
    )