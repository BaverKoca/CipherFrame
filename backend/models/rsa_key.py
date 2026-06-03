"""RSA key pair model for Cipher Frame users."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base
from backend.models.common import utc_now


class RSAKeyPair(Base):
    """Stored RSA key pair metadata for secure DES session key exchange."""

    __tablename__ = "rsa_key_pairs"
    __table_args__ = (
        Index("ix_rsa_key_pairs_user_id", "user_id"),
        Index("ix_rsa_key_pairs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    private_key_pem_encrypted_placeholder: Mapped[str] = mapped_column(Text, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="rsa_keypairs")