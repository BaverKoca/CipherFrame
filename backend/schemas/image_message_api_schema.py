"""API schemas for encrypted image messaging in Cipher Frame."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.user_schema import UserSummary


class ImageSendResponse(BaseModel):
    """Response returned after a successful image send."""

    message_id: int
    receiver: UserSummary
    timestamp: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class InboxMessageItem(BaseModel):
    """Inbox listing item without decrypted content."""

    message_id: int
    sender: UserSummary
    timestamp: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class SentMessageItem(BaseModel):
    """Sent listing item without decrypted content."""

    message_id: int
    receiver: UserSummary
    timestamp: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class MessageContentResponse(BaseModel):
    """Full decrypted message response for the receiver."""

    message_id: int
    sender: UserSummary
    filename: str = Field(min_length=1)
    signature_valid: bool
    timestamp: datetime
    image_base64: str

    model_config = ConfigDict(from_attributes=True)


class MessageVerificationResponse(BaseModel):
    """Signature verification result for a message."""

    message_id: int
    signature_valid: bool
    image_hash: str

    model_config = ConfigDict(from_attributes=True)