"""RSA helpers for Cipher Frame key exchange and key storage."""

from base64 import b64decode, b64encode

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA


def generate_rsa_keypair() -> RSA.RsaKey:
    """Generate a new 2048-bit RSA private key."""

    return RSA.generate(2048)


def export_public_key_pem(key_pair: RSA.RsaKey) -> str:
    """Export the RSA public key in PEM format."""

    return key_pair.publickey().export_key(format="PEM").decode("utf-8")


def export_private_key_pem(key_pair: RSA.RsaKey, passphrase: str | None = None) -> str:
    """Export the RSA private key in PEM format."""

    export_kwargs = {"format": "PEM"}
    if passphrase:
        export_kwargs["passphrase"] = passphrase
        export_kwargs["pkcs"] = 8
        export_kwargs["protection"] = "scryptAndAES128-CBC"
    return key_pair.export_key(**export_kwargs).decode("utf-8")


def rsa_encrypt(data: bytes, public_key_pem: str) -> str:
    """Encrypt bytes with RSA-OAEP and return base64 text."""

    rsa_key = RSA.import_key(public_key_pem)
    cipher = PKCS1_OAEP.new(rsa_key)
    ciphertext = cipher.encrypt(data)
    return b64encode(ciphertext).decode("utf-8")


def rsa_decrypt(ciphertext_b64: str, private_key_pem: str, passphrase: str | None = None) -> bytes:
    """Decrypt base64 ciphertext with RSA-OAEP."""

    rsa_key = RSA.import_key(private_key_pem, passphrase=passphrase)
    cipher = PKCS1_OAEP.new(rsa_key)
    ciphertext = b64decode(ciphertext_b64)
    return cipher.decrypt(ciphertext)