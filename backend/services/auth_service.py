"""Authentication business logic for Cipher Frame."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.server_log import LogLevel
from backend.models.user import User, UserRole
from backend.schemas.auth_schema import UserLogin, UserRegister
from backend.schemas.user_schema import UserRead
from backend.services.log_service import create_server_log
from backend.services.password_service import hash_password, verify_password
from backend.services.token_service import create_access_token


def user_to_read_schema(user: User) -> UserRead:
    """Convert a SQLAlchemy user model into a response schema."""

    return UserRead.model_validate(user)


def register_user(session: Session, payload: UserRegister, *, ip_address: str | None = None) -> UserRead:
    """Register a new client user while preventing duplicate usernames and emails."""

    duplicate_user = session.scalar(
        select(User.id).where((User.username == payload.username) | (User.email == payload.email)).limit(1)
    )
    if duplicate_user is not None:
        create_server_log(
            session,
            level=LogLevel.WARNING,
            event_type="registration_failed_duplicate",
            message=f"Duplicate registration attempt for username={payload.username} email={payload.email}",
            ip_address=ip_address,
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists.")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.CLIENT,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    create_server_log(
        session,
        level=LogLevel.INFO,
        event_type="registration_success",
        message=f"Client registration succeeded for user_id={user.id} username={user.username}",
        actor_user_id=user.id,
        ip_address=ip_address,
    )
    return user_to_read_schema(user)


def authenticate_user(session: Session, payload: UserLogin, *, ip_address: str | None = None) -> tuple[User, str]:
    """Validate credentials and return the user with a new JWT token."""

    user = session.scalar(select(User).where(User.username == payload.username).limit(1))
    if user is None:
        create_server_log(
            session,
            level=LogLevel.WARNING,
            event_type="login_failed",
            message=f"Failed login for unknown username={payload.username}",
            ip_address=ip_address,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    if not user.is_active:
        create_server_log(
            session,
            level=LogLevel.WARNING,
            event_type="inactive_user_login_attempt",
            message=f"Inactive login attempt for user_id={user.id} username={user.username}",
            actor_user_id=user.id,
            ip_address=ip_address,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account.")

    if not verify_password(payload.password, user.password_hash):
        create_server_log(
            session,
            level=LogLevel.WARNING,
            event_type="login_failed",
            message=f"Failed login for user_id={user.id} username={user.username}",
            actor_user_id=user.id,
            ip_address=ip_address,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role.value)
    create_server_log(
        session,
        level=LogLevel.INFO,
        event_type="login_success",
        message=f"Successful login for user_id={user.id} username={user.username}",
        actor_user_id=user.id,
        ip_address=ip_address,
    )
    return user, token