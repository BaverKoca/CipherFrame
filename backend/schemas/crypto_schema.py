"""Utility schemas for cryptography test endpoints."""

from pydantic import BaseModel, Field


class DESRoundTripRequest(BaseModel):
    """Payload for a DES round-trip test."""

    plaintext: str = Field(min_length=1)


class RSARoundTripRequest(BaseModel):
    """Payload for an RSA round-trip test."""

    plaintext: str = Field(min_length=1)


class SignatureTestRequest(BaseModel):
    """Payload for a signing and verification test."""

    data: str = Field(min_length=1)