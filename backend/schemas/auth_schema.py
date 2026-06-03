"""Authentication schemas for Cipher Frame."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.schemas.user_schema import UserRead


class UserRegister(BaseModel):
    """Payload for user registration."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class UserLogin(BaseModel):
    """Payload for username/password login."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    """JWT access token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT payload fields used for authentication."""

    sub: str | None = None
    role: str | None = None


class AuthUserResponse(BaseModel):
    """Standard authenticated user response that excludes password hashes."""

    user: UserRead

    model_config = ConfigDict(from_attributes=True)