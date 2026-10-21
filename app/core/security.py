"""
Password hashing.

Uses bcrypt over a SHA-256 pre-hash to bypass bcrypt's 72-byte input
limit safely. Two passwords that share the first 72 bytes would otherwise
produce the same hash under plain bcrypt. Pre-hashing with SHA-256
produces fixed 44-byte base64 input, so the full password contributes.

Hash format is a bcrypt hash of `base64(sha256(password))`. Existing
plain-bcrypt hashes MUST be rehashed on next successful login — call
`needs_rehash()` after `verify_password()` returns True.
"""

from __future__ import annotations

import base64
import hashlib

import bcrypt

from app.core.config import settings


def _prehash(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(_prehash(password), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True when the stored hash should be replaced.

    Covers (a) legacy plain-bcrypt hashes (no SHA-256 pre-hash) and
    (b) hashes produced with a different BCRYPT_ROUNDS than configured.
    """
    try:
        parts = hashed.split("$")
        if len(parts) < 4 or not parts[1].startswith("2"):
            return True
        return int(parts[2]) != settings.BCRYPT_ROUNDS
    except (ValueError, IndexError):
        return True