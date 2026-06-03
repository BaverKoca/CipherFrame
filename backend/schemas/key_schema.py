"""RSA key pair schemas for Cipher Frame API responses and future endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RSAKeyPairBase(BaseModel):
    """Shared RSA key pair fields."""

    user_id: int
    public_key_pem: str = Field(min_length=1)
    key_version: int = Field(default=1, ge=1)
    is_active: bool = True
    expires_at: datetime | None = None


class RSAKeyPairCreate(RSAKeyPairBase):
    """Payload for storing a newly generated RSA key pair."""

    private_key_pem_encrypted_placeholder: str = Field(min_length=1)


class RSAKeyPairRead(RSAKeyPairBase):
    """Read model that omits the private key placeholder from API responses."""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)