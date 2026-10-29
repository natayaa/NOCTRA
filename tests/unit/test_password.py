"""Password hashing tests."""

from app.core.security import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    hashed = hash_password("correcthorsebattery")
    assert verify_password("correcthorsebattery", hashed)


def test_wrong_password_rejected():
    hashed = hash_password("correcthorsebattery")
    assert not verify_password("wrongpassword123", hashed)


def test_hashes_are_unique_due_to_salt():
    h1 = hash_password("samesame")
    h2 = hash_password("samesame")
    assert h1 != h2
    assert verify_password("samesame", h1)
    assert verify_password("samesame", h2)


def test_long_passwords_use_bytes_beyond_72():
    """SHA-256 pre-hashing means bcrypt's 72-byte limit never truncates.

    Two passwords that share their first 72 bytes must NOT verify against
    each other — under plain bcrypt they would.
    """
    base = "a" * 72
    hashed = hash_password(base + "X")
    assert verify_password(base + "X", hashed)
    assert not verify_password(base + "Y", hashed)


def test_malformed_hash_returns_false():
    assert not verify_password("anything", "not-a-bcrypt-hash")
    assert not verify_password("anything", "")