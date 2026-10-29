from typing import Annotated, NewType
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, StringConstraints

# Rupiah amount — stored as BIGINT
Rupiah = Annotated[int, AfterValidator(lambda v: int(v))]

# Human-readable IDs (NOCTRA-2026-000123, INV-2026-000045)
HumanCode = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9\-]{3,64}$")]

UserId = NewType("UserId", UUID)


def _validate_email(value: str) -> str:
    """Validate an address, allowing this app's internal `.local` domain.

    NOCTRA's own addresses (`hello@noctra.local`, seeded staff accounts,
    test fixtures) use the reserved `.local` suffix. `pydantic.EmailStr`
    rejects reserved/special-use domains unconditionally — even with
    `test_environment=True`, which only permits `.test` — so a user with a
    `.local` address made `/api/v1/auth/me` and every response schema
    validating that email return 500.

    The address is validated as-is, except that a `.local` domain is
    swapped for `.test` for the syntax/deliverability checks (both are
    permitted by `test_environment=True`); the original value is returned
    so stored data is never rewritten.
    """
    addr = value.strip()
    if not addr:
        raise ValueError("email must not be empty")

    candidate = addr
    if "@" in addr:
        local_part, _, domain = addr.rpartition("@")
        labels = domain.split(".")
        if len(labels) > 1 and labels[-1].lower() == "local":
            candidate = f"{local_part}@{'.'.join(labels[:-1] + ['test'])}"

    try:
        validate_email(
            candidate,
            check_deliverability=False,
            test_environment=True,
        )
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return addr


# Validated email address (accepts the internal `.local` domain).
Email = Annotated[str, AfterValidator(_validate_email)]
