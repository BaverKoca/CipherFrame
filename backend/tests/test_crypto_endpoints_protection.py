"""Test that crypto test endpoints require admin authorization."""

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


def main() -> None:
    """Verify crypto test endpoints are protected by admin-only access."""

    init_db()
    session_factory = get_session_maker()
    client = TestClient(app)

    # Create a non-admin client user
    client_username = f"crypto_test_user_{uuid4().hex[:8]}"
    client_email = f"{client_username}@example.com"
    client_password = "StrongPassword123!"

    with client:
        # Register the client user
        register_response = client.post(
            "/api/auth/register",
            json={"username": client_username, "email": client_email, "password": client_password},
        )
        assert register_response.status_code == 201

        # Authenticate as admin
        admin_login = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "ChangeMe123!"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]

        # Authenticate as client user
        client_login = client.post(
            "/api/auth/login",
            json={"username": client_username, "password": client_password},
        )
        assert client_login.status_code == 200
        client_token = client_login.json()["access_token"]

        # Test /api/crypto/test/des with client user (should get 403)
        des_client_response = client.post(
            "/api/crypto/test/des",
            headers={"Authorization": f"Bearer {client_token}"},
            json={"plaintext": "test data"},
        )
        assert des_client_response.status_code == 403
        assert "Admin access required" in des_client_response.json()["detail"]

        # Test /api/crypto/test/des with admin user (should succeed)
        des_admin_response = client.post(
            "/api/crypto/test/des",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"plaintext": "test data"},
        )
        assert des_admin_response.status_code == 200
        assert des_admin_response.json()["success"] is True

        # Test /api/crypto/test/rsa with client user (should get 403)
        rsa_client_response = client.post(
            "/api/crypto/test/rsa",
            headers={"Authorization": f"Bearer {client_token}"},
            json={"plaintext": "test data"},
        )
        assert rsa_client_response.status_code == 403
        assert "Admin access required" in rsa_client_response.json()["detail"]

        # Test /api/crypto/test/rsa with admin user (should succeed)
        rsa_admin_response = client.post(
            "/api/crypto/test/rsa",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"plaintext": "test data"},
        )
        assert rsa_admin_response.status_code == 200
        assert rsa_admin_response.json()["success"] is True

        # Test /api/crypto/test/signature with client user (should get 403)
        sig_client_response = client.post(
            "/api/crypto/test/signature",
            headers={"Authorization": f"Bearer {client_token}"},
            json={"data": "test data"},
        )
        assert sig_client_response.status_code == 403
        assert "Admin access required" in sig_client_response.json()["detail"]

        # Test /api/crypto/test/signature with admin user (should succeed)
        sig_admin_response = client.post(
            "/api/crypto/test/signature",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"data": "test data"},
        )
        assert sig_admin_response.status_code == 200
        assert sig_admin_response.json()["verified"] is True

    print("All crypto endpoint protection checks passed.")


if __name__ == "__main__":
    main()
