"""Shared permission dependencies for admin web routers."""

from __future__ import annotations

from fastapi import Depends

from app.core.constants import PermissionCode
from app.modules.auth.dependencies import require_permission


def read(perm: PermissionCode):
    """Require a READ permission on the endpoint."""
    return Depends(require_permission(perm))


def write(perm: PermissionCode):
    """Require a WRITE permission on the endpoint."""
    return Depends(require_permission(perm))