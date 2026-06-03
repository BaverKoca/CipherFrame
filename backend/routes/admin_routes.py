"""Administrative routes for Cipher Frame."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.database import get_db
from backend.dependencies.auth_dependencies import require_admin
from backend.models.admin_action import AdminAction
from backend.models.image_message import ImageMessage, MessageStatus
from backend.models.rsa_key import RSAKeyPair
from backend.models.server_log import LogLevel, ServerLog
from backend.models.user import User
from backend.schemas.admin_schema import (
    AdminKeyRead,
    AdminMessageRead,
    AdminOverviewRead,
    AdminServerLogRead,
    AdminUserRead,
    AdminUserStatusUpdate,
)
from backend.services.crypto.key_rotation_service import rotate_user_rsa_keys
from backend.websocket.websocket_service import connection_manager

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _record_admin_action(
    db: Session,
    *,
    admin_user: User,
    action_type: str,
    target_user: User | None,
    description: str,
) -> None:
    """Persist a privileged admin action and a matching server log entry."""

    db.add(
        AdminAction(
            admin_user_id=admin_user.id,
            action_type=action_type,
            target_user_id=target_user.id if target_user is not None else None,
            description=description,
        )
    )
    db.add(
        ServerLog(
            level=LogLevel.INFO,
            event_type=action_type,
            message=description,
            actor_user_id=admin_user.id,
        )
    )
    db.commit()


@router.get("/overview", response_model=AdminOverviewRead)
async def get_overview(db: Session = Depends(get_db), current_user: User = Depends(require_admin)) -> AdminOverviewRead:
    """Return dashboard-wide operational metrics."""

    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    active_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    inactive_users = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(False))) or 0
    total_messages = db.scalar(select(func.count()).select_from(ImageMessage)) or 0
    delivered_messages = db.scalar(
        select(func.count()).select_from(ImageMessage).where(ImageMessage.status == MessageStatus.DELIVERED)
    ) or 0
    failed_messages = db.scalar(
        select(func.count()).select_from(ImageMessage).where(ImageMessage.status == MessageStatus.FAILED)
    ) or 0
    total_server_logs = db.scalar(select(func.count()).select_from(ServerLog)) or 0
    online_users_count = len(await connection_manager.get_online_users())

    return AdminOverviewRead(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        total_messages=total_messages,
        delivered_messages=delivered_messages,
        failed_messages=failed_messages,
        online_users_count=online_users_count,
        total_server_logs=total_server_logs,
    )


@router.get("/users", response_model=list[AdminUserRead])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(require_admin)) -> list[AdminUserRead]:
    """Return all users for administrative monitoring."""

    users = db.scalars(select(User).order_by(User.created_at.desc(), User.id.desc())).all()
    return [AdminUserRead.model_validate(user) for user in users]


@router.patch("/users/{user_id}/status", response_model=AdminUserRead)
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminUserRead:
    """Enable or disable a user account."""

    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if current_user.id == target_user.id and payload.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrators cannot disable themselves.")

    target_user.is_active = payload.is_active
    db.add(target_user)
    _record_admin_action(
        db,
        admin_user=current_user,
        target_user=target_user,
        action_type="admin_user_status_update",
        description=(
            f"Admin user_id={current_user.id} set user_id={target_user.id} active={payload.is_active} "
            f"from {request.client.host if request.client else 'unknown'}"
        ),
    )
    return AdminUserRead.model_validate(target_user)


@router.get("/messages", response_model=list[AdminMessageRead])
def list_messages(db: Session = Depends(get_db), current_user: User = Depends(require_admin)) -> list[AdminMessageRead]:
    """Return encrypted message metadata with sender and receiver context."""

    sender_user = aliased(User)
    receiver_user = aliased(User)
    rows = db.execute(
        select(ImageMessage, sender_user.username, receiver_user.username)
        .join(sender_user, ImageMessage.sender_id == sender_user.id)
        .join(receiver_user, ImageMessage.receiver_id == receiver_user.id)
        .order_by(ImageMessage.created_at.desc(), ImageMessage.id.desc())
    ).all()
    return [
        AdminMessageRead(
            message_id=image_message.id,
            sender_username=sender_username,
            receiver_username=receiver_username,
            original_filename=image_message.original_filename,
            status=image_message.status,
            created_at=image_message.created_at,
            delivered_at=image_message.delivered_at,
            encryption_algorithm=image_message.encryption_algorithm,
            signature_algorithm=image_message.signature_algorithm,
        )
        for image_message, sender_username, receiver_username in rows
    ]


@router.get("/logs", response_model=list[AdminServerLogRead])
def list_logs(
    level: LogLevel | None = Query(default=None),
    event_type: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> list[AdminServerLogRead]:
    """Return filtered server logs for admin review."""

    query = select(ServerLog, User.username).outerjoin(User, ServerLog.actor_user_id == User.id)
    if level is not None:
        query = query.where(ServerLog.level == level)
    if event_type:
        query = query.where(ServerLog.event_type == event_type)
    query = query.order_by(ServerLog.created_at.desc(), ServerLog.id.desc()).limit(limit)

    entries = []
    for log_entry, actor_username in db.execute(query).all():
        entries.append(
            AdminServerLogRead(
                id=log_entry.id,
                level=log_entry.level,
                event_type=log_entry.event_type,
                message=log_entry.message,
                actor=actor_username,
                ip_address=log_entry.ip_address,
                created_at=log_entry.created_at,
            )
        )
    return entries


@router.get("/keys", response_model=list[AdminKeyRead])
def list_keys(db: Session = Depends(get_db), current_user: User = Depends(require_admin)) -> list[AdminKeyRead]:
    """Return RSA key metadata for all users."""

    rows = db.execute(
        select(RSAKeyPair, User.username)
        .join(User, RSAKeyPair.user_id == User.id)
        .order_by(User.username.asc(), RSAKeyPair.key_version.desc(), RSAKeyPair.created_at.desc())
    ).all()
    return [
        AdminKeyRead(
            username=username,
            key_version=key_pair.key_version,
            is_active=key_pair.is_active,
            created_at=key_pair.created_at,
            expires_at=key_pair.expires_at,
        )
        for key_pair, username in rows
    ]


@router.post("/users/{user_id}/rotate-keys", response_model=AdminKeyRead)
def rotate_user_keys(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> AdminKeyRead:
    """Manually rotate a user's RSA key pair."""

    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    key_pair = rotate_user_rsa_keys(db, target_user.id)
    _record_admin_action(
        db,
        admin_user=current_user,
        target_user=target_user,
        action_type="admin_rotate_user_keys",
        description=(
            f"Admin user_id={current_user.id} rotated RSA keys for user_id={target_user.id} "
            f"version={key_pair.key_version} from {request.client.host if request.client else 'unknown'}"
        ),
    )
    return AdminKeyRead(
        username=target_user.username,
        key_version=key_pair.key_version,
        is_active=key_pair.is_active,
        created_at=key_pair.created_at,
        expires_at=key_pair.expires_at,
    )