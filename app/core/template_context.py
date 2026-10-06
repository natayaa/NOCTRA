from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TemplateContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not hasattr(request.state, "user"):
            request.state.user = None
        if not hasattr(request.state, "flashes"):
            request.state.flashes = []
        if not hasattr(request.state, "csrf_token"):
            request.state.csrf_token = ""
        return await call_next(request)