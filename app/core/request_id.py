import re
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id: ContextVar[str] = ContextVar("request_id", default="")

# Only allow identifier-like characters — anything else (newlines, ANSI
# escapes, control bytes) could forge log lines or corrupt response headers.
_VALID_RID = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")


def get_request_id() -> str:
    return _request_id.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        raw = (request.headers.get(self.HEADER) or "").strip()
        rid = raw if _VALID_RID.match(raw) else uuid.uuid4().hex

        request.state.request_id = rid
        token = _request_id.set(rid)
        try:
            response = await call_next(request)
            response.headers[self.HEADER] = rid
            return response
        finally:
            _request_id.reset(token)