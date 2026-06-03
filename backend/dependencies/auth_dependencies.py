"""Authentication and authorization dependencies for Cipher Frame."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User, UserRole
from backend.schemas.auth_schema import TokenData
from backend.services.token_service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_user_from_token(db: Session, token: str) -> User:
    """Resolve a user from a JWT bearer token."""

    try:
        payload = decode_access_token(token)
        token_data = TokenData(sub=payload.get("sub"), role=payload.get("role"))
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.") from exc

    if token_data.sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.")

    user = db.get(User, int(token_data.sub))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account.")
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Resolve the current authenticated user from a bearer token."""

    return get_user_from_token(db, token)


def require_client(current_user: User = Depends(get_current_user)) -> User:
    """Require the authenticated user to have the client role."""

    if current_user.role != UserRole.CLIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client access required.")
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the authenticated user to have the admin role."""

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user