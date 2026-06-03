"""Integration-style websocket verification for Cipher Frame chat connectivity."""

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
from backend.models.user import User
from backend.services.crypto.key_rotation_service import rotate_user_rsa_keys


PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\x99c````\x00\x00\x00\x05\x00\x01\x0d\n*\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


def _drain_initial_events(websocket, expected_event: str) -> dict:
    """Read websocket events until the expected one appears."""

    while True:
        payload = websocket.receive_json()
        if payload.get("event") == expected_event:
            return payload


def main() -> None:
    """Run websocket connectivity and notification checks."""

    init_db()
    session_factory = get_session_maker()
    client = TestClient(app)

    receiver_username = f"ws_receiver_{uuid4().hex[:8]}"
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

        sender_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "ChangeMe123!"},
        )
        assert sender_login.status_code == 200
        sender_token = sender_login.json()["access_token"]

        receiver_login = client.post(
            "/api/auth/login",
            json={"username": receiver_username, "password": receiver_password},
        )
        assert receiver_login.status_code == 200
        receiver_token = receiver_login.json()["access_token"]

        with client.websocket_connect(f"/ws/chat?token={sender_token}") as sender_ws, client.websocket_connect(
            f"/ws/chat?token={receiver_token}"
        ) as receiver_ws:
            sender_connected = sender_ws.receive_json()
            assert sender_connected["event"] == "user_connected"

            receiver_connected = receiver_ws.receive_json()
            assert receiver_connected["event"] == "user_connected"

            online_users_response = client.get(
                "/api/chat/online-users",
                headers={"Authorization": f"Bearer {receiver_token}"},
            )
            assert online_users_response.status_code == 200
            assert len(online_users_response.json()) == 2

            send_response = client.post(
                "/api/messages/send-image",
                headers={"Authorization": f"Bearer {sender_token}"},
                files={"file": ("cipher.png", BytesIO(PNG_BYTES), "image/png")},
                data={"receiver_username": receiver_username},
            )
            assert send_response.status_code == 200
            message_id = send_response.json()["message_id"]

            receiver_event = _drain_initial_events(receiver_ws, "message_notification")
            assert receiver_event["data"]["message_id"] == message_id

            message_response = client.get(
                f"/api/messages/{message_id}",
                headers={"Authorization": f"Bearer {receiver_token}"},
            )
            assert message_response.status_code == 200

            sender_delivery_event = _drain_initial_events(sender_ws, "image_delivered")
            assert sender_delivery_event["data"]["message_id"] == message_id

        invalid_ws_failed = False
        try:
            with client.websocket_connect("/ws/chat?token=invalid-token"):
                pass
        except Exception:
            invalid_ws_failed = True
        assert invalid_ws_failed is True

    print("All Cipher Frame websocket checks passed.")


if __name__ == "__main__":
    main()