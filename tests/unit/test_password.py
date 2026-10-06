"""Password hashing tests."""

from app.core.security import hash_password, verify_password


def test_hash_and_verify_roundtrip():
    hashed = hash_password("correcthorsebattery")
    assert verify_password("correcthorsebattery", hashed)


def test_wrong_password_rejected():
    hashed = hash_password("correcthorsebattery")
    assert not verify_password("wrongpassword123", hashed)


def test_hashes_are_unique():
    """Same input → different hash each time (random salt)."""
    h1 = hash_password("samesame")
    h2 = hash_password("samesame")
    assert h1 != h2
    assert verify_password("samesame", h1)
    assert verify_password("samesame", h2)


def test_long_password_is_truncated_at_72_bytes():
    """
    bcrypt truncates at 72 bytes. Two passwords that share the first
    72 bytes should produce hashes that verify each other.
    """
    base = "a" * 72
    hashed = hash_password(base + "X")
    # Same 72-byte prefix → verification succeeds
    assert verify_password(base + "Y", hashed)


def test_verify_malformed_hash_returns_false():
    assert not verify_password("anything", "not-a-bcrypt-hash")
    assert not verify_password("anything", "")