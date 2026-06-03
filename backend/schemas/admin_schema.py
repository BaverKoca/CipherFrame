"""Administrative schemas for Cipher Frame API responses and admin endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.image_message import MessageStatus
from backend.models.server_log import LogLevel
from backend.models.user import UserRole


class AdminOverviewRead(BaseModel):
    """Aggregate metrics for the admin dashboard."""

    total_users: int
    active_users: int
    inactive_users: int
    total_messages: int
    delivered_messages: int
    failed_messages: int
    online_users_count: int
    total_server_logs: int


class AdminUserRead(BaseModel):
    """Admin-facing user listing."""

    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserStatusUpdate(BaseModel):
    """Payload to enable or disable a user account."""

    is_active: bool


class AdminMessageRead(BaseModel):
    """Admin-facing encrypted message metadata."""

    message_id: int
    sender_username: str
    receiver_username: str
    original_filename: str
    status: MessageStatus
    created_at: datetime
    delivered_at: datetime | None = None
    encryption_algorithm: str
    signature_algorithm: str


class AdminServerLogRead(BaseModel):
    """Admin-facing server log entry with actor context."""

    id: int
    level: LogLevel
    event_type: str = Field(min_length=1, max_length=100)
    message: str
    actor: str | None = None
    ip_address: str | None = None
    created_at: datetime


class AdminKeyRead(BaseModel):
    """Admin-facing RSA key metadata."""

    username: str
    key_version: int
    is_active: bool
    created_at: datetime
    expires_at: datetime | None = None


class ServerLogRead(BaseModel):
    """Read model for persistent server log entries."""

    id: int
    level: LogLevel
    event_type: str = Field(min_length=1, max_length=100)
    message: str
    actor_user_id: int | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminActionBase(BaseModel):
    """Shared admin action payload fields."""

    admin_user_id: int
    action_type: str = Field(min_length=1, max_length=100)
    target_user_id: int | None = None
    description: str = Field(min_length=1)


class AdminActionCreate(AdminActionBase):
    """Payload for future admin action creation endpoints."""


class AdminActionRead(AdminActionBase):
    """Read model for administrative audit records."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)