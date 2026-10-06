from __future__ import annotations

import bcrypt

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hash a plaintext password with bcrypt.

    Truncates to bcrypt's 72-byte limit as required by the algorithm.
    Uses cost factor from settings.BCRYPT_ROUNDS.
    """
    pw_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Returns False on any error rather than raising, so login flows
    treat malformed hashes as failed attempts.
    """
    try:
        pw_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pw_bytes, hashed_bytes)
    except (ValueError, TypeError):
        return False