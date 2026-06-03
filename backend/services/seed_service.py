"""Database seeding utilities for Cipher Frame."""

from sqlalchemy import or_, select

from backend.config import get_settings
from backend.database import get_session_maker
from backend.models.user import User, UserRole
from backend.services.password_service import hash_password, verify_password


def seed_default_admin() -> bool:
    """Create a default admin user if one does not already exist.

    Returns True when the admin account is created or updated and False otherwise.
    """

    settings = get_settings()
    session_factory = get_session_maker()

    with session_factory() as session:
        existing_admin = session.scalar(select(User).where(User.role == UserRole.ADMIN).limit(1))
        if existing_admin is not None:
            if not verify_password(settings.default_admin_password, existing_admin.password_hash):
                existing_admin.password_hash = hash_password(settings.default_admin_password)
                session.commit()
                return True
            return False

        conflicting_user = session.scalar(
            select(User.id).where(
                or_(
                    User.username == settings.default_admin_username,
                    User.email == settings.default_admin_email,
                )
            ).limit(1)
        )
        if conflicting_user is not None:
            return False

        admin_user = User(
            username=settings.default_admin_username,
            email=settings.default_admin_email,
            password_hash=hash_password(settings.default_admin_password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)
        session.commit()
        session.refresh(admin_user)
        return True