"""Integration-style verification for Cipher Frame admin dashboard endpoints."""

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
from backend.models.user import User
from backend.services.crypto.key_rotation_service import rotate_user_rsa_keys


PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0cIDAT\x08\x99c````\x00\x00\x00\x05\x00\x01\r\n*\xb4\x00\x00\x00\x00IEND\xaeB`\x82"


def main() -> None:
    """Run the admin dashboard verification checks."""

    init_db()
    session_factory = get_session_maker()
    client = TestClient(app)

    client_username = f"admin_client_{uuid4().hex[:8]}"
    client_email = f"{client_username}@example.com"
    client_password = "StrongPassword123!"

    with client:
        register_response = client.post(
            "/api/auth/register",
            json={"username": client_username, "email": client_email, "password": client_password},
        )
        assert register_response.status_code == 201

        with session_factory() as session:
            admin_user = session.query(User).filter(User.username == "admin").one()
            client_user = session.query(User).filter(User.username == client_username).one()
            rotate_user_rsa_keys(session, admin_user.id)
            rotate_user_rsa_keys(session, client_user.id)

        admin_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "ChangeMe123!"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]

        client_login = client.post(
            "/api/auth/login",
            json={"username": client_username, "password": client_password},
        )
        assert client_login.status_code == 200
        client_token = client_login.json()["access_token"]

        overview_response = client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert overview_response.status_code == 200
        overview_payload = overview_response.json()
        assert overview_payload["total_users"] >= 2
        assert overview_payload["active_users"] >= 2
        assert overview_payload["online_users_count"] >= 0

        client_overview_response = client.get(
            "/api/admin/overview",
            headers={"Authorization": f"Bearer {client_token}"},
        )
        assert client_overview_response.status_code == 403

        users_response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert users_response.status_code == 200
        users_payload = users_response.json()
        assert any(item["username"] == client_username for item in users_payload)

        disable_response = client.patch(
            f"/api/admin/users/{client_user.id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False},
        )
        assert disable_response.status_code == 200
        assert disable_response.json()["is_active"] is False

        client_after_disable_response = client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {client_token}"},
        )
        assert client_after_disable_response.status_code == 403

        enable_response = client.patch(
            f"/api/admin/users/{client_user.id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": True},
        )
        assert enable_response.status_code == 200
        assert enable_response.json()["is_active"] is True

        self_disable_response = client.patch(
            f"/api/admin/users/{admin_user.id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False},
        )
        assert self_disable_response.status_code == 400

        send_response = client.post(
            "/api/messages/send-image",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("admin-message.png", BytesIO(PNG_BYTES), "image/png")},
            data={"receiver_username": client_username},
        )
        assert send_response.status_code == 200
        message_id = send_response.json()["message_id"]

        messages_response = client.get(
            "/api/admin/messages",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert messages_response.status_code == 200
        messages_payload = messages_response.json()
        assert any(item["message_id"] == message_id for item in messages_payload)

        logs_response = client.get(
            "/api/admin/logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert logs_response.status_code == 200
        logs_payload = logs_response.json()
        assert len(logs_payload) > 0
        assert all("event_type" in item for item in logs_payload)

        filtered_logs_response = client.get(
            "/api/admin/logs",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"event_type": "admin_user_status_update", "limit": 10},
        )
        assert filtered_logs_response.status_code == 200
        assert all(item["event_type"] == "admin_user_status_update" for item in filtered_logs_response.json())

        keys_response = client.get(
            "/api/admin/keys",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert keys_response.status_code == 200
        assert any(item["username"] == client_username for item in keys_response.json())

        key_count_before = len(keys_response.json())
        rotate_response = client.post(
            f"/api/admin/users/{client_user.id}/rotate-keys",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert rotate_response.status_code == 200
        rotate_payload = rotate_response.json()
        assert rotate_payload["username"] == client_username
        assert rotate_payload["key_version"] >= 1

        keys_after_response = client.get(
            "/api/admin/keys",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert keys_after_response.status_code == 200
        assert len(keys_after_response.json()) >= key_count_before + 1

    print("All Cipher Frame admin dashboard checks passed.")


if __name__ == "__main__":
    main()