from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenPayload(BaseModel):
    sub: str
    typ: Literal["access", "refresh"]
    iat: int
    exp: int
    jti: str
    iss: str
    extra: dict[str, Any] = {}


def _encode(sub: str, typ: str, expires: timedelta, extra: dict | None = None) -> str:
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
    return _encode(sub, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), extra)


def create_refresh_token(sub: str) -> str:
    return _encode(sub, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str) -> TokenPayload:
    try:
        raw = jwt.decode(
            token,
            settings.APP_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    return TokenPayload.model_validate(raw)