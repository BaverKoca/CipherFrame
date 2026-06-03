"""RSA key rotation logic for Cipher Frame."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.rsa_key import RSAKeyPair
from backend.models.user import User
from backend.models.server_log import LogLevel
from backend.services.crypto.rsa_service import export_private_key_pem, export_public_key_pem, generate_rsa_keypair
from backend.services.log_service import create_server_log


def rotate_user_rsa_keys(session: Session, user_id: int) -> RSAKeyPair:
    """Create a new RSA key pair version for a user and deactivate the old key."""

    user = session.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found.")

    current_key = session.scalar(
        select(RSAKeyPair)
        .where(RSAKeyPair.user_id == user_id)
        .order_by(RSAKeyPair.key_version.desc())
        .limit(1)
    )
    next_version = 1 if current_key is None else current_key.key_version + 1

    private_key = generate_rsa_keypair()
    public_pem = export_public_key_pem(private_key)
    private_pem = export_private_key_pem(private_key)

    create_server_log(
        session,
        level=LogLevel.INFO,
        event_type="rsa_key_generation",
        message=f"RSA key generated for user_id={user_id} version={next_version}",
        actor_user_id=user_id,
    )

    if current_key is not None:
        current_key.is_active = False
        session.add(current_key)

    new_key = RSAKeyPair(
        user_id=user_id,
        public_key_pem=public_pem,
        private_key_pem_encrypted_placeholder=private_pem,
        key_version=next_version,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),
    )
    session.add(new_key)
    session.commit()
    session.refresh(new_key)

    create_server_log(
        session,
        level=LogLevel.INFO,
        event_type="rsa_key_rotation",
        message=f"RSA key rotation completed for user_id={user_id} version={next_version}",
        actor_user_id=user_id,
    )
    return new_key