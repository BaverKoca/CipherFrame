"""Unit-test-style verification script for Cipher Frame cryptography core."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import init_db, get_session_maker
from backend.main import app
from backend.models.rsa_key import RSAKeyPair
from backend.models.user import User
from backend.services.seed_service import seed_default_admin
from backend.services.crypto.des_service import decrypt_bytes_des, encrypt_bytes_des, generate_des_key
from backend.services.crypto.hash_service import sha256_hash_bytes, sha256_hash_file
from backend.services.crypto.key_rotation_service import rotate_user_rsa_keys
from backend.services.crypto.rsa_service import (
    export_private_key_pem,
    export_public_key_pem,
    generate_rsa_keypair,
    rsa_decrypt,
    rsa_encrypt,
)
from backend.services.crypto.signature_service import sign_data, verify_signature


def main() -> None:
    """Run the crypto verification checks and print the outcomes."""

    init_db()
    seed_default_admin()
    session_factory = get_session_maker()

    with session_factory() as session:
        user = session.query(User).filter(User.username == "admin").one()
        previous_keys = session.query(RSAKeyPair).filter(RSAKeyPair.user_id == user.id).all()

        des_key = generate_des_key()
        des_ciphertext, des_iv = encrypt_bytes_des(b"cipher frame des test", des_key)
        des_plaintext = decrypt_bytes_des(des_ciphertext, des_key, des_iv)
        assert des_plaintext == b"cipher frame des test"

        rsa_private_key = generate_rsa_keypair()
        rsa_public_pem = export_public_key_pem(rsa_private_key)
        rsa_private_pem = export_private_key_pem(rsa_private_key)
        rsa_ciphertext = rsa_encrypt(b"cipher frame rsa test", rsa_public_pem)
        rsa_plaintext = rsa_decrypt(rsa_ciphertext, rsa_private_pem)
        assert rsa_plaintext == b"cipher frame rsa test"

        signature = sign_data(b"cipher frame signature test", rsa_private_pem)
        assert verify_signature(b"cipher frame signature test", signature, rsa_public_pem)

        digest_a = sha256_hash_bytes(b"same-data")
        digest_b = sha256_hash_bytes(b"same-data")
        assert digest_a == digest_b

        temp_file = Path("storage") / "crypto_test_payload.bin"
        temp_file.write_bytes(b"file-hash-test")
        try:
            file_hash_a = sha256_hash_file(temp_file)
            file_hash_b = sha256_hash_file(temp_file)
            assert file_hash_a == file_hash_b
        finally:
            temp_file.unlink(missing_ok=True)

        rotated_key = rotate_user_rsa_keys(session, user.id)
        assert rotated_key.user_id == user.id
        assert rotated_key.is_active is True
        assert rotated_key.key_version >= 1
        if previous_keys:
            assert any(key.is_active is False for key in previous_keys)
        assert session.query(RSAKeyPair).filter(RSAKeyPair.user_id == user.id).count() >= len(previous_keys) + 1

    print("All Cipher Frame crypto checks passed.")


if __name__ == "__main__":
    main()