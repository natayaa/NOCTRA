from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import log
from app.core.request_id import get_request_id


def _payload(code: str, message: str, *, details=None) -> dict:
    body = {
        "error": {
            "code": code,
            "message": message,
            "request_id": get_request_id(),
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def _safe_errors(errors: list[dict], *, include_ctx: bool) -> list[dict]:
    """Strip non-serialisable / secret-bearing fields from Pydantic errors.

    `ctx` may hold the raw `ValueError`/`TypeError` instance raised by a
    custom validator — a plain `JSONResponse` would choke on it. `input`
    echoes request data back to the caller and can leak passwords/tokens.
    """
    out = []
    for err in errors:
        item = {k: v for k, v in err.items() if k != "input"}
        if "url" in item:
            item["url"] = str(item["url"])
        if include_ctx and "ctx" in item and isinstance(item["ctx"], dict):
            item["ctx"] = {
                k: (str(v) if isinstance(v, BaseException) else v)
                for k, v in item["ctx"].items()
            }
        else:
            item.pop("ctx", None)
        out.append(item)
    return out


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        log.warning(
            "app_error",
            code=exc.code,
            message=exc.message,
            path=request.url.path,
            context=exc.context,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        safe = _safe_errors(exc.errors(), include_ctx=settings.APP_DEBUG)
        return JSONResponse(
            status_code=422,
            content=_payload(
                "validation_error",
                "Invalid input",
                details=jsonable_encoder(safe),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(f"http_{exc.status_code}", str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> Response:
        log.exception(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        if settings.APP_DEBUG:
            raise exc
        return JSONResponse(
            status_code=500,
            content=_payload("internal_error", "Internal server error"),
        )