"""Temporary cryptography test routes for Cipher Frame."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth_dependencies import require_admin
from backend.models.user import User
from backend.schemas.crypto_schema import DESRoundTripRequest, RSARoundTripRequest, SignatureTestRequest
from backend.services.crypto.des_service import decrypt_bytes_des, encrypt_bytes_des, generate_des_key
from backend.services.crypto.hash_service import sha256_hash_bytes
from backend.services.crypto.key_rotation_service import rotate_user_rsa_keys
from backend.services.crypto.rsa_service import (
    export_private_key_pem,
    export_public_key_pem,
    generate_rsa_keypair,
    rsa_decrypt,
    rsa_encrypt,
)
from backend.services.crypto.signature_service import sign_data, verify_signature
from backend.services.log_service import create_server_log
from backend.models.server_log import LogLevel

router = APIRouter(prefix="/api/crypto", tags=["Crypto"])


@router.post("/test/des")
def test_des_round_trip(
    payload: DESRoundTripRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, str | bool]:
    """Run a DES encrypt/decrypt test using the requested plaintext."""

    try:
        key = generate_des_key()
        ciphertext, iv = encrypt_bytes_des(payload.plaintext.encode("utf-8"), key)
    except Exception as exc:
        create_server_log(db, level=LogLevel.ERROR, event_type="encryption_failure", message=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DES test failed.") from exc

    try:
        decrypted = decrypt_bytes_des(ciphertext, key, iv).decode("utf-8")
        return {"success": decrypted == payload.plaintext, "ciphertext": ciphertext, "iv": iv}
    except Exception as exc:
        create_server_log(db, level=LogLevel.ERROR, event_type="decryption_failure", message=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DES test failed.") from exc


@router.post("/test/rsa")
def test_rsa_round_trip(
    payload: RSARoundTripRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, str | bool]:
    """Run an RSA encrypt/decrypt test using the requested plaintext."""

    try:
        key_pair = generate_rsa_keypair()
        public_pem = export_public_key_pem(key_pair)
        private_pem = export_private_key_pem(key_pair)
        ciphertext = rsa_encrypt(payload.plaintext.encode("utf-8"), public_pem)
        create_server_log(db, level=LogLevel.INFO, event_type="rsa_key_generation", message="RSA test key generated")
    except Exception as exc:
        create_server_log(db, level=LogLevel.ERROR, event_type="encryption_failure", message=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="RSA test failed.") from exc

    try:
        decrypted = rsa_decrypt(ciphertext, private_pem).decode("utf-8")
        return {"success": decrypted == payload.plaintext, "ciphertext": ciphertext}
    except Exception as exc:
        create_server_log(db, level=LogLevel.ERROR, event_type="decryption_failure", message=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="RSA test failed.") from exc


@router.post("/test/signature")
def test_signature_round_trip(
    payload: SignatureTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, bool | str]:
    """Run a signing and verification test."""

    try:
        key_pair = generate_rsa_keypair()
        public_pem = export_public_key_pem(key_pair)
        private_pem = export_private_key_pem(key_pair)
        signature = sign_data(payload.data.encode("utf-8"), private_pem)
        verified = verify_signature(payload.data.encode("utf-8"), signature, public_pem)
        create_server_log(db, level=LogLevel.INFO, event_type="image_signature_created", message="Signature test executed")
        if not verified:
            create_server_log(db, level=LogLevel.WARNING, event_type="signature_verification_failure", message="Signature test failed")
        return {"verified": verified, "signature": signature, "hash": sha256_hash_bytes(payload.data.encode("utf-8"))}
    except Exception as exc:
        create_server_log(db, level=LogLevel.ERROR, event_type="signature_verification_failure", message=str(exc))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Signature test failed.") from exc