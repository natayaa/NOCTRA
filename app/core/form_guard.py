"""Signed render timestamps for public forms.

A hidden, HMAC-signed timestamp tells the server when the form was
rendered by us. Two cheap bot signals fall out of it without a captcha:

- submissions faster than a human can fill the form ("too_fast")
- submissions from a page left open past its usefulness ("expired")

The token is not a security boundary like CSRF — a determined crawler
can request the form and wait. It removes the cheapest scripted spam,
which is most of it. Rejections are answered with the normal success
redirect so bots get no signal to tune against.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from app.core.config import settings

_PREFIX = "form-ts"


def _sign(timestamp: int) -> str:
    message = f"{_PREFIX}:{timestamp}".encode()
    return hmac.new(
        settings.APP_SECRET_KEY.encode(), message, hashlib.sha256
    ).hexdigest()[:32]


def make_form_timestamp(*, now: float | None = None) -> str:
    ts = int(time.time() if now is None else now)
    return f"{ts}.{_sign(ts)}"


def check_form_timestamp(
    token: str | None,
    *,
    min_age_seconds: int | None = None,
    max_age_seconds: int | None = None,
) -> tuple[bool, str]:
    """Return `(ok, reason)`. Reasons are logged, never shown to the user."""
    if not token:
        return False, "missing"
    try:
        raw_ts, signature = token.split(".", 1)
        ts = int(raw_ts)
    except (ValueError, AttributeError):
        return False, "malformed"

    if not hmac.compare_digest(signature, _sign(ts)):
        return False, "bad_signature"

    min_age = (
        settings.PUBLIC_INTAKE_MIN_FILL_SECONDS
        if min_age_seconds is None
        else min_age_seconds
    )
    max_age = (
        settings.PUBLIC_INTAKE_FORM_TTL_SECONDS
        if max_age_seconds is None
        else max_age_seconds
    )

    age = time.time() - ts
    # A few seconds of clock skew between the render and submit is fine;
    # a timestamp from the future is not.
    if age < 0 and abs(age) > 60:
        return False, "future_timestamp"
    if age < min_age:
        return False, "too_fast"
    if age > max_age:
        return False, "expired"
    return True, "ok"
