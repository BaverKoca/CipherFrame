"""Hashing utilities for Cipher Frame."""

from hashlib import sha256
from pathlib import Path


def sha256_hash_bytes(data: bytes) -> str:
    """Return a SHA-256 hex digest for raw bytes."""

    return sha256(data).hexdigest()


def sha256_hash_file(file_path: str | Path) -> str:
    """Return a SHA-256 hex digest for a file's contents."""

    hasher = sha256()
    with Path(file_path).open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()