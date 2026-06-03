"""Encrypted image messaging routes for Cipher Frame."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth_dependencies import get_current_user
from backend.models.user import User
from backend.services.image_message_service import (
    get_message_for_receiver,
    list_inbox_messages,
    list_sent_messages,
    send_image_message,
    verify_message_signature,
)

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.post("/send-image")
async def send_image(
    request: Request,
    receiver_username: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send an encrypted image message to an active receiver."""

    image_bytes = await file.read()
    return send_image_message(
        db,
        sender=current_user,
        receiver_username=receiver_username,
        upload_file=file,
        image_bytes=image_bytes,
        ip_address=request.client.host if request.client else None,
    )


@router.get("/inbox")
def inbox(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return the authenticated user's inbox without decrypted content."""

    return list_inbox_messages(db, user=current_user)


@router.get("/sent")
def sent(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Return the authenticated user's sent messages."""

    return list_sent_messages(db, user=current_user)


@router.get("/{message_id}")
def read_message(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Decrypt and return a message for its receiver."""

    return get_message_for_receiver(db, user=current_user, message_id=message_id)


@router.get("/{message_id}/verify")
def verify_message(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Verify a message signature and return the stored image hash."""

    return verify_message_signature(db, user=current_user, message_id=message_id)