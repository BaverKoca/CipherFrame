"""DES encryption helpers for Cipher Frame."""

from base64 import b64decode, b64encode

from Crypto.Cipher import DES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad


BLOCK_SIZE = DES.block_size


def generate_des_key() -> str:
    """Generate an 8-byte DES key encoded as URL-safe base64 text."""

    return b64encode(get_random_bytes(BLOCK_SIZE)).decode("utf-8")


def encrypt_bytes_des(plaintext: bytes, des_key_b64: str) -> tuple[str, str]:
    """Encrypt bytes with DES-CBC and return base64 ciphertext and IV."""

    key = b64decode(des_key_b64)
    if len(key) != BLOCK_SIZE:
        raise ValueError("DES key must decode to exactly 8 bytes.")

    iv = get_random_bytes(BLOCK_SIZE)
    cipher = DES.new(key, DES.MODE_CBC, iv=iv)
    ciphertext = cipher.encrypt(pad(plaintext, BLOCK_SIZE))
    return b64encode(ciphertext).decode("utf-8"), b64encode(iv).decode("utf-8")


def decrypt_bytes_des(ciphertext_b64: str, des_key_b64: str, iv_b64: str) -> bytes:
    """Decrypt base64 ciphertext with DES-CBC and PKCS7 unpadding."""

    key = b64decode(des_key_b64)
    iv = b64decode(iv_b64)
    ciphertext = b64decode(ciphertext_b64)
    if len(key) != BLOCK_SIZE:
        raise ValueError("DES key must decode to exactly 8 bytes.")
    if len(iv) != BLOCK_SIZE:
        raise ValueError("DES IV must decode to exactly 8 bytes.")

    cipher = DES.new(key, DES.MODE_CBC, iv=iv)
    return unpad(cipher.decrypt(ciphertext), BLOCK_SIZE)