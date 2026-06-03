"""Encrypted image messaging business logic for Cipher Frame."""

from base64 import b64decode, b64encode
from datetime import datetime, timezone
from email.mime import message
import imghdr
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.image_message import ImageMessage, MessageStatus
from backend.models.rsa_key import RSAKeyPair
from backend.models.server_log import LogLevel
from backend.models.user import User
from backend.schemas.image_message_api_schema import ImageSendResponse, InboxMessageItem, MessageContentResponse, MessageVerificationResponse, SentMessageItem
from backend.schemas.user_schema import UserSummary
from backend.services.crypto.des_service import decrypt_bytes_des, encrypt_bytes_des, generate_des_key
from backend.services.crypto.hash_service import sha256_hash_bytes
from backend.services.crypto.rsa_service import rsa_decrypt, rsa_encrypt
from backend.services.crypto.signature_service import sign_data, verify_signature
from backend.services.log_service import create_server_log
from backend.websocket.websocket_service import notify_user_event


def get_encrypted_images_directory() -> Path:
    """Return the directory used to store encrypted image payloads."""

    directory = Path(__file__).resolve().parents[2] / "storage" / "encrypted_images"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _get_active_rsa_key(session: Session, user_id: int) -> RSAKeyPair:
    """Return the active RSA key pair for a user."""

    key_pair = session.scalar(
        select(RSAKeyPair)
        .where(RSAKeyPair.user_id == user_id, RSAKeyPair.is_active.is_(True))
        .order_by(RSAKeyPair.key_version.desc())
        .limit(1)
    )
    if key_pair is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active RSA key pair required.")
    return key_pair


def _user_to_summary(user: User) -> UserSummary:
    """Convert a user ORM object into a compact schema."""

    return UserSummary.model_validate(user)


def _validate_image_upload(upload_file: UploadFile, image_bytes: bytes) -> str:
    """Validate size and file type before encryption."""

    settings = get_settings()
    if len(image_bytes) > settings.max_image_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image exceeds size limit.")

    detected_type = imghdr.what(None, h=image_bytes)
    if detected_type is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported or invalid image type.")

    allowed_types = {image_type.lower() for image_type in settings.allowed_image_types}
    if detected_type.lower() not in allowed_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported or invalid image type.")

    if not upload_file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is required.")

    return detected_type.lower()


def send_image_message(
    session: Session,
    *,
    sender: User,
    receiver_username: str,
    upload_file: UploadFile,
    image_bytes: bytes,
    ip_address: str | None = None,
) -> ImageSendResponse:
    """Encrypt and persist an image message for a receiver."""

    try:
        try:
            _validate_image_upload(upload_file, image_bytes)
        except HTTPException as exc:
            create_server_log(
                session,
                level=LogLevel.WARNING,
                event_type="encryption_failure",
                message=f"Image validation failed for sender_id={sender.id}: {exc.detail}",
                actor_user_id=sender.id,
                ip_address=ip_address,
            )
            raise

        receiver = session.scalar(select(User).where(User.username == receiver_username).limit(1))
        if receiver is None or not receiver.is_active:
            create_server_log(
                session,
                level=LogLevel.WARNING,
                event_type="unauthorized_access",
                message=f"Invalid receiver username={receiver_username} for sender_id={sender.id}",
                actor_user_id=sender.id,
                ip_address=ip_address,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receiver not found or inactive.")

        sender_key = _get_active_rsa_key(session, sender.id)
        receiver_key = _get_active_rsa_key(session, receiver.id)

        des_key = generate_des_key()
        encrypted_image_b64, iv_b64 = encrypt_bytes_des(image_bytes, des_key)
        encrypted_image_bytes = b64decode(iv_b64) + b64decode(encrypted_image_b64)

        message_hash = sha256_hash_bytes(image_bytes)
        signature = sign_data(image_bytes, sender_key.private_key_pem_encrypted_placeholder)
        encrypted_des_key = rsa_encrypt(des_key.encode("utf-8"), receiver_key.public_key_pem)

        encrypted_dir = get_encrypted_images_directory()
        stored_name = f"{uuid4().hex}.enc"
        encrypted_path = encrypted_dir / stored_name
        encrypted_path.write_bytes(encrypted_image_bytes)

        message = ImageMessage(
            sender_id=sender.id,
            receiver_id=receiver.id,
            original_filename=upload_file.filename,
            encrypted_image_path=str(encrypted_path.as_posix()),
            encrypted_des_key=encrypted_des_key,
            des_key_encryption_algorithm="RSA-OAEP",
            digital_signature=signature,
            image_hash=message_hash,
            signature_algorithm="RSA-PKCS1v1.5-SHA256",
            encryption_algorithm="DES-CBC",
            status=MessageStatus.SENT,
        )
        session.add(message)
        session.commit()
        session.refresh(message)

        create_server_log(
            session,
            level=LogLevel.INFO,
            event_type="image_sent",
            message=f"Image sent from sender_id={sender.id} to receiver_id={receiver.id} message_id={message.id}",
            actor_user_id=sender.id,
            ip_address=ip_address,
        )

        notification_payload = {
            "message_id": message.id,
            "sender": {"user_id": sender.id, "username": sender.username},
            "receiver": {"user_id": receiver.id, "username": receiver.username},
            "filename": message.original_filename,
            "timestamp": message.created_at.isoformat(),
            "status": message.status.value,
        }
        notify_user_event(receiver.id, "message_notification", notification_payload)
        notify_user_event(sender.id, "image_sent", notification_payload)

        return ImageSendResponse(
            message_id=message.id,
            receiver=_user_to_summary(receiver),
            timestamp=message.created_at,
            status=message.status.value,
        )
    except HTTPException:
        raise
    except Exception as exc:
        create_server_log(
            session,
            level=LogLevel.ERROR,
            event_type="encryption_failure",
            message=str(exc),
            actor_user_id=sender.id,
            ip_address=ip_address,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send image.") from exc


def list_inbox_messages(session: Session, *, user: User) -> list[InboxMessageItem]:
    """Return messages sent to the authenticated user."""

    messages = session.scalars(
        select(ImageMessage)
        .where(ImageMessage.receiver_id == user.id)
        .order_by(ImageMessage.created_at.desc())
    ).all()
    return [
        InboxMessageItem(
            message_id=message.id,
            sender=_user_to_summary(message.sender),
            timestamp=message.created_at,
            status=message.status.value,
        )
        for message in messages
    ]


def list_sent_messages(session: Session, *, user: User) -> list[SentMessageItem]:
    """Return messages sent by the authenticated user."""

    messages = session.scalars(
        select(ImageMessage)
        .where(ImageMessage.sender_id == user.id)
        .order_by(ImageMessage.created_at.desc())
    ).all()
    return [
        SentMessageItem(
            message_id=message.id,
            receiver=_user_to_summary(message.receiver),
            timestamp=message.created_at,
            status=message.status.value,
        )
        for message in messages
    ]


def get_message_for_receiver(session: Session, *, user: User, message_id: int) -> MessageContentResponse:
    """Decrypt and verify a message for its receiver."""

    message = session.get(ImageMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    if message.receiver_id != user.id:
        create_server_log(
            session,
            level=LogLevel.WARNING,
            event_type="unauthorized_access",
            message=f"Unauthorized message access attempt for message_id={message_id} by user_id={user.id}",
            actor_user_id=user.id,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the receiver can decrypt this image.")

    receiver_key = _get_active_rsa_key(session, user.id)
    sender = session.get(User, message.sender_id)
    if sender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender not found.")

    try:
        des_key = rsa_decrypt(message.encrypted_des_key, receiver_key.private_key_pem_encrypted_placeholder).decode("utf-8")
        encrypted_path = Path(message.encrypted_image_path)
        encrypted_image_bytes = encrypted_path.read_bytes()
        iv = encrypted_image_bytes[:8]
        ciphertext = encrypted_image_bytes[8:]
        image_bytes = decrypt_bytes_des(b64encode(ciphertext).decode("utf-8"), des_key, b64encode(iv).decode("utf-8"))
        signature_valid = verify_signature(image_bytes, message.digital_signature, _get_active_rsa_key(session, sender.id).public_key_pem)
        if not signature_valid:
            message.status = MessageStatus.FAILED
            session.add(message)
            session.commit()
            create_server_log(
                session,
                level=LogLevel.WARNING,
                event_type="invalid_signature",
                message=f"Invalid signature for message_id={message.id}",
                actor_user_id=user.id,
            )
            notify_user_event(
                sender.id,
                "signature_verification_failed",
                {"message_id": message.id, "sender": {"user_id": sender.id, "username": sender.username}},
            )
        else:
            message.status = MessageStatus.DELIVERED
            message.delivered_at = datetime.now(timezone.utc)
            session.add(message)
            session.commit()
            create_server_log(
                session,
                level=LogLevel.INFO,
                event_type="image_delivered",
                message=f"Image delivered for message_id={message.id}",
                actor_user_id=user.id,
            )
            notify_user_event(
                sender.id,
                "image_delivered",
                {
                    "message_id": message.id,
                    "receiver": {"user_id": user.id, "username": user.username},
                    "timestamp": message.delivered_at.isoformat() if message.delivered_at else message.created_at.isoformat(),
                    "status": message.status.value,
                },
            )

        return MessageContentResponse(
            message_id=message.id,
            sender=_user_to_summary(sender),
            filename=message.original_filename,
            signature_valid=signature_valid,
            timestamp=message.created_at,
            image_base64=b64encode(image_bytes).decode("utf-8"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        message.status = MessageStatus.FAILED
        session.add(message)
        session.commit()
        create_server_log(
            session,
            level=LogLevel.ERROR,
            event_type="decryption_failure",
            message=f"Failed to decrypt message_id={message.id}: {exc}",
            actor_user_id=user.id,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to decrypt image.") from exc


def verify_message_signature(session: Session, *, user: User, message_id: int) -> MessageVerificationResponse:
    """Verify a message signature after decrypting the stored image."""

    message = session.get(ImageMessage, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")

    if user.id not in {message.sender_id, message.receiver_id}:
        create_server_log(
            session,
            level=LogLevel.WARNING,
            event_type="unauthorized_access",
            message=f"Unauthorized signature verification for message_id={message_id} by user_id={user.id}",
            actor_user_id=user.id,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    receiver_key = _get_active_rsa_key(session, message.receiver_id)
    sender_key = _get_active_rsa_key(session, message.sender_id)

    sender = session.get(User, message.sender_id)
    if sender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender not found.")

    try:
        des_key = rsa_decrypt(message.encrypted_des_key, receiver_key.private_key_pem_encrypted_placeholder).decode("utf-8")
        encrypted_path = Path(message.encrypted_image_path)
        encrypted_image_bytes = encrypted_path.read_bytes()
        iv = encrypted_image_bytes[:8]
        ciphertext = encrypted_image_bytes[8:]
        image_bytes = decrypt_bytes_des(b64encode(ciphertext).decode("utf-8"), des_key, b64encode(iv).decode("utf-8"))
        image_hash = sha256_hash_bytes(image_bytes)
        signature_valid = verify_signature(image_bytes, message.digital_signature, sender_key.public_key_pem)

        if not signature_valid:
            create_server_log(
                session,
                level=LogLevel.WARNING,
                event_type="invalid_signature",
                message=f"Signature verification failed for message_id={message.id}",
                actor_user_id=user.id,
            )
            message.status = MessageStatus.FAILED
            session.add(message)
            session.commit()
            notify_user_event(
                sender.id,
                "signature_verification_failed",
                {"message_id": message.id, "sender": {"user_id": sender.id, "username": sender.username}},
            )

        return MessageVerificationResponse(message_id=message.id, signature_valid=signature_valid, image_hash=image_hash)
    except HTTPException:
        raise
    except Exception as exc:
        create_server_log(
            session,
            level=LogLevel.ERROR,
            event_type="decryption_failure",
            message=f"Failed to verify message_id={message.id}: {exc}",
            actor_user_id=user.id,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify message.") from exc