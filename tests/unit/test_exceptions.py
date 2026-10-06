"""AppError hierarchy tests — Phase 1."""

from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
)


def test_app_error_defaults():
    err = AppError()
    assert err.status_code == 500
    assert err.code == "internal_error"
    assert err.message == "Internal server error"
    assert err.context == {}


def test_app_error_custom_message():
    err = AppError("Boom")
    assert str(err) == "Boom"
    assert err.message == "Boom"


def test_app_error_custom_code_and_context():
    err = AppError("Boom", code="custom", context={"x": 1})
    assert err.code == "custom"
    assert err.context == {"x": 1}


def test_not_found_status():
    assert NotFoundError().status_code == 404
    assert NotFoundError().code == "not_found"


def test_conflict_status():
    assert ConflictError().status_code == 409
    assert ConflictError().code == "conflict"


def test_unauthorized_status():
    assert UnauthorizedError().status_code == 401
    assert UnauthorizedError().code == "unauthorized"


def test_forbidden_status():
    assert ForbiddenError().status_code == 403
    assert ForbiddenError().code == "forbidden"


def test_validation_status():
    assert ValidationError().status_code == 422
    assert ValidationError().code == "validation_error"


def test_rate_limit_status():
    assert RateLimitError().status_code == 429


def test_all_errors_subclass_app_error():
    for cls in (
        NotFoundError,
        ConflictError,
        UnauthorizedError,
        ForbiddenError,
        ValidationError,
        RateLimitError,
    ):
        assert issubclass(cls, AppError)