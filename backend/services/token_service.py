"""JWT token helpers for Cipher Frame authentication."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from backend.config import get_settings

ALGORITHM = "HS256"


def create_access_token(subject: str, role: str, expires_delta_minutes: int | None = None) -> str:
    """Create a signed JWT access token."""

    settings = get_settings()
    expire_minutes = expires_delta_minutes if expires_delta_minutes is not None else settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""

    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def is_token_invalid(token: str) -> bool:
    """Return True when a token cannot be decoded."""

    try:
        decode_access_token(token)
        return False
    except JWTError:
        return True