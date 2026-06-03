"""User schemas for Cipher Frame API responses and future endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.models.user import UserRole


class UserBase(BaseModel):
    """Shared user fields for request and response models."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole = UserRole.CLIENT
    is_active: bool = True


class UserCreate(UserBase):
    """User payload for future registration or admin provisioning endpoints."""

    password: str = Field(min_length=12, max_length=128)


class UserRead(UserBase):
    """Public-facing user representation returned by API endpoints."""

    id: int
    created_at: datetime
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserSummary(BaseModel):
    """Compact user summary for nested API payloads."""

    id: int
    username: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)