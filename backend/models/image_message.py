"""Encrypted image message model for Cipher Frame."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.common import utc_now


class MessageStatus(str, PyEnum):
    """Delivery state for encrypted image messages."""

    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class ImageMessage(Base):
    """Encrypted image payload metadata exchanged between clients."""

    __tablename__ = "image_messages"
    __table_args__ = (
        Index("ix_image_messages_sender_id", "sender_id"),
        Index("ix_image_messages_receiver_id", "receiver_id"),
        Index("ix_image_messages_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    encrypted_des_key: Mapped[str] = mapped_column(Text, nullable=False)
    des_key_encryption_algorithm: Mapped[str] = mapped_column(String(50), default="RSA-OAEP", nullable=False)
    digital_signature: Mapped[str] = mapped_column(Text, nullable=False)
    image_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(String(50), default="RSA-SHA256", nullable=False)
    encryption_algorithm: Mapped[str] = mapped_column(String(50), default="DES", nullable=False)
    status: Mapped[MessageStatus] = mapped_column(
        SQLEnum(
            MessageStatus,
            name="message_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            native_enum=False,
            create_constraint=True,
        ),
        default=MessageStatus.SENT,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="image_messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="image_messages_received")