"""Digital signature helpers for Cipher Frame."""

from base64 import b64decode, b64encode

from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.PublicKey import RSA


def sign_data(data: bytes, private_key_pem: str, passphrase: str | None = None) -> str:
    """Create an RSA PKCS#1 v1.5 signature over SHA-256(data)."""

    rsa_key = RSA.import_key(private_key_pem, passphrase=passphrase)
    digest = SHA256.new(data)
    signature = pkcs1_15.new(rsa_key).sign(digest)
    return b64encode(signature).decode("utf-8")


def verify_signature(data: bytes, signature_b64: str, public_key_pem: str) -> bool:
    """Verify an RSA PKCS#1 v1.5 signature over SHA-256(data)."""

    rsa_key = RSA.import_key(public_key_pem)
    digest = SHA256.new(data)
    signature = b64decode(signature_b64)
    try:
        pkcs1_15.new(rsa_key).verify(digest, signature)
        return True
    except (ValueError, TypeError):
        return False