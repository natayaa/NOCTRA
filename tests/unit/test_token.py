"""JWT creation and decoding tests."""

from uuid import uuid4

import pytest

from app.core.tokens import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_access_token_roundtrip():
    uid = str(uuid4())
    token = create_access_token(uid, {"username": "ivan"})
    payload = decode_token(token)
    assert payload.sub == uid
    assert payload.typ == "access"
    assert payload.extra["username"] == "ivan"


def test_refresh_token_type():
    token = create_refresh_token(str(uuid4()))
    payload = decode_token(token)
    assert payload.typ == "refresh"


def test_tokens_have_unique_jti():
    a = decode_token(create_access_token(str(uuid4())))
    b = decode_token(create_access_token(str(uuid4())))
    assert a.jti != b.jti


def test_invalid_token_raises():
    with pytest.raises(ValueError):
        decode_token("not.a.real.token")


def test_tampered_token_raises():
    token = create_access_token(str(uuid4()))
    tampered = token[:-4] + "xxxx"
    with pytest.raises(ValueError):
        decode_token(tampered)