from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

TokenType = Literal["access", "refresh"]


class TokenPayload(BaseModel):
    sub: str
    typ: TokenType
    iat: int
    exp: int
    jti: str
    iss: str
    extra: dict[str, Any] = {}


def _encode(
    sub: str, typ: TokenType, expires: timedelta, extra: dict | None = None
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sub,
        "typ": typ,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
        "jti": uuid4().hex,
        "iss": settings.JWT_ISSUER,
        "extra": extra or {},
    }
    return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(sub: str, extra: dict | None = None) -> str:
    return _encode(
        sub,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra,
    )


def create_refresh_token(sub: str) -> str:
    return _encode(sub, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, *, expected_typ: TokenType | None = None) -> TokenPayload:
    """
    Decode and validate a JWT.

    Pass `expected_typ="access"` or `"refresh"` to prevent typ confusion
    (a refresh token being accepted where an access token is required, or
    vice versa). Prefer the `decode_access_token` / `decode_refresh_token`
    helpers below.
    """
    try:
        raw = jwt.decode(
            token,
            settings.APP_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    payload = TokenPayload.model_validate(raw)
    if expected_typ is not None and payload.typ != expected_typ:
        raise ValueError(f"Expected {expected_typ} token, got {payload.typ}")
    return payload


def decode_access_token(token: str) -> TokenPayload:
    return decode_token(token, expected_typ="access")


def decode_refresh_token(token: str) -> TokenPayload:
    return decode_token(token, expected_typ="refresh")