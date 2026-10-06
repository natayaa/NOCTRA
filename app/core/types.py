from typing import Annotated, NewType
from uuid import UUID

from pydantic import AfterValidator, StringConstraints

# Rupiah amount — stored as BIGINT
Rupiah = Annotated[int, AfterValidator(lambda v: int(v))]

# Human-readable IDs (NOCTRA-2026-000123, INV-2026-000045)
HumanCode = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9\-]{3,64}$")]

UserId = NewType("UserId", UUID)