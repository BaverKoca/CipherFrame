"""Integration-style verification for Cipher Frame encrypted image messaging."""

from base64 import b64decode
from io import BytesIO
from pathlib import Path
import sys
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from backend.database import get_session_maker, init_db
from backend.main import app
from backend.models.rsa_key import RSAKeyPair
from backend.models.user import User
from backend.services.crypto.key_rotation_service import rotate_user_rsa_keys


PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\x99c````\x00\x00\x00\x05\x00\x01\x0d\n*\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


def main() -> None:
    """Run the encrypted image messaging verification checks."""

    init_db()
    session_factory = get_session_maker()
    client = TestClient(app)

    receiver_username = f"receiver_{uuid4().hex[:8]}"
    receiver_email = f"{receiver_username}@example.com"
    receiver_password = "StrongPassword123!"

    with client:
        register_response = client.post(
            "/api/auth/register",
            json={"username": receiver_username, "email": receiver_email, "password": receiver_password},
        )
        assert register_response.status_code == 201

        with session_factory() as session:
            sender = session.query(User).filter(User.username == "admin").one()
            receiver = session.query(User).filter(User.username == receiver_username).one()
            rotate_user_rsa_keys(session, sender.id)
            rotate_user_rsa_keys(session, receiver.id)
            assert session.query(RSAKeyPair).filter(RSAKeyPair.user_id == sender.id).count() >= 1
            assert session.query(RSAKeyPair).filter(RSAKeyPair.user_id == receiver.id).count() >= 1

        sender_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "ChangeMe123!"},
        )
        assert sender_login.status_code == 200
        sender_token = sender_login.json()["access_token"]

        send_response = client.post(
            "/api/messages/send-image",
            headers={"Authorization": f"Bearer {sender_token}"},
            files={"file": ("cipher.png", BytesIO(PNG_BYTES), "image/png")},
            data={"receiver_username": receiver_username},
        )
        assert send_response.status_code == 200
        send_payload = send_response.json()
        message_id = send_payload["message_id"]
        assert send_payload["status"] == "sent"

        inbox_as_sender = client.get(
            "/api/messages/inbox",
            headers={"Authorization": f"Bearer {sender_token}"},
        )
        assert inbox_as_sender.status_code == 200
        assert inbox_as_sender.json() == []

        receiver_login = client.post(
            "/api/auth/login",
            json={"username": receiver_username, "password": receiver_password},
        )
        assert receiver_login.status_code == 200
        receiver_token = receiver_login.json()["access_token"]

        inbox_response = client.get(
            "/api/messages/inbox",
            headers={"Authorization": f"Bearer {receiver_token}"},
        )
        assert inbox_response.status_code == 200
        inbox_items = inbox_response.json()
        assert len(inbox_items) == 1
        assert inbox_items[0]["message_id"] == message_id

        message_response = client.get(
            f"/api/messages/{message_id}",
            headers={"Authorization": f"Bearer {receiver_token}"},
        )
        assert message_response.status_code == 200
        message_payload = message_response.json()
        assert message_payload["message_id"] == message_id
        assert message_payload["signature_valid"] is True
        assert b64decode(message_payload["image_base64"]) == PNG_BYTES

        verify_response = client.get(
            f"/api/messages/{message_id}/verify",
            headers={"Authorization": f"Bearer {receiver_token}"},
        )
        assert verify_response.status_code == 200
        verify_payload = verify_response.json()
        assert verify_payload["message_id"] == message_id
        assert verify_payload["signature_valid"] is True

        sent_response = client.get(
            "/api/messages/sent",
            headers={"Authorization": f"Bearer {sender_token}"},
        )
        assert sent_response.status_code == 200
        assert len(sent_response.json()) == 1

        unauthorized_response = client.get(
            f"/api/messages/{message_id}",
            headers={"Authorization": f"Bearer {sender_token}"},
        )
        assert unauthorized_response.status_code == 403

    print("All Cipher Frame image message checks passed.")


if __name__ == "__main__":
    main()
