"""Image message schemas for Cipher Frame API responses and future endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.image_message import MessageStatus


class ImageMessageBase(BaseModel):
    """Common encrypted image message fields."""

    sender_id: int
    receiver_id: int
    original_filename: str = Field(min_length=1, max_length=255)
    encrypted_image_path: str = Field(min_length=1, max_length=512)
    encrypted_des_key: str = Field(min_length=1)
    des_key_encryption_algorithm: str = Field(default="RSA-OAEP", min_length=1, max_length=50)
    digital_signature: str = Field(min_length=1)
    image_hash: str = Field(min_length=1, max_length=255)
    signature_algorithm: str = Field(default="RSA-SHA256", min_length=1, max_length=50)
    encryption_algorithm: str = Field(default="DES", min_length=1, max_length=50)
    status: MessageStatus = MessageStatus.SENT


class ImageMessageCreate(ImageMessageBase):
    """Payload for future message creation endpoints."""


class ImageMessageRead(ImageMessageBase):
    """Stored encrypted image message returned by API endpoints."""

    id: int
    created_at: datetime
    delivered_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)