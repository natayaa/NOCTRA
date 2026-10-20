"""RBAC role + permission defaults."""

from __future__ import annotations

from app.core.constants import PermissionCode, RoleName


# ════════════════════════════════════════════════════════════════
# DEFAULT ROLE → PERMISSION MAP
#
# Applied by `seed.py::seed_default_rbac` on startup or via migration.
# Additive only — seeding never removes an existing permission from a
# role (removals must be explicit admin actions).
#
# RoleName.SUPERUSER auto-includes every PermissionCode by construction,
# so new permissions are automatically granted to superusers.
# ════════════════════════════════════════════════════════════════

DEFAULT_ROLE_PERMISSIONS: dict[str, set[PermissionCode]] = {
    RoleName.SUPERUSER: set(PermissionCode),

    RoleName.ADMIN: {
        # Phase 1 — users & audit & settings
        PermissionCode.USER_READ,
        PermissionCode.USER_CREATE,
        PermissionCode.USER_UPDATE,
        PermissionCode.ROLE_READ,
        PermissionCode.AUDIT_READ,
        PermissionCode.SETTINGS_READ,
        PermissionCode.SETTINGS_UPDATE,
        # Phase 2a — customers & vehicles
        PermissionCode.CUSTOMER_READ,
        PermissionCode.CUSTOMER_WRITE,
        PermissionCode.CUSTOMER_DELETE,
        PermissionCode.VEHICLE_READ,
        PermissionCode.VEHICLE_WRITE,
        PermissionCode.VEHICLE_DELETE,
        # Phase 2b — inquiries
        PermissionCode.INQUIRY_READ,
        PermissionCode.INQUIRY_CREATE,
        PermissionCode.INQUIRY_UPDATE,
        PermissionCode.INQUIRY_ASSIGN,
        PermissionCode.INQUIRY_CLOSE,
        # Phase 3 — inventory & suppliers
        PermissionCode.INVENTORY_READ,
        PermissionCode.INVENTORY_WRITE,
        PermissionCode.INVENTORY_TRANSACT,
        PermissionCode.INVENTORY_ADJUST,
        PermissionCode.INVENTORY_PURCHASE,
        PermissionCode.SUPPLIER_READ,
        PermissionCode.SUPPLIER_WRITE,
        # Phase 4 — projects & employees
        PermissionCode.PROJECT_READ,
        PermissionCode.PROJECT_CREATE,
        PermissionCode.PROJECT_UPDATE,
        PermissionCode.PROJECT_COST,
        PermissionCode.PROJECT_APPROVE,
        PermissionCode.PROJECT_DELETE,
        PermissionCode.EMPLOYEE_READ,
        PermissionCode.EMPLOYEE_WRITE,
        # Phase 5 — pricing
        PermissionCode.PRICING_READ,
        PermissionCode.PRICING_WRITE,
        # Phase 6 — finance
        PermissionCode.FINANCE_READ,
        PermissionCode.INVOICE_WRITE,
        PermissionCode.PAYMENT_WRITE,
        PermissionCode.EXPENSE_WRITE,
        PermissionCode.FINANCE_REPORTS,
        # Phase 7 — analytics
        PermissionCode.ANALYTICS_READ,
    },

    RoleName.SALES: {
        PermissionCode.USER_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.CUSTOMER_WRITE,
        PermissionCode.VEHICLE_READ,
        PermissionCode.VEHICLE_WRITE,
        # Inquiries — sales owns the pipeline
        PermissionCode.INQUIRY_READ,
        PermissionCode.INQUIRY_CREATE,
        PermissionCode.INQUIRY_UPDATE,
        PermissionCode.INQUIRY_ASSIGN,
        PermissionCode.INQUIRY_CLOSE,
        # Inventory — read only + supplier read
        PermissionCode.INVENTORY_READ,
        PermissionCode.SUPPLIER_READ,
        # Projects — can create and approve, not delete
        PermissionCode.PROJECT_READ,
        PermissionCode.PROJECT_CREATE,
        PermissionCode.PROJECT_UPDATE,
        PermissionCode.PROJECT_APPROVE,
        PermissionCode.EMPLOYEE_READ,
        # Pricing & finance — read only
        PermissionCode.PRICING_READ,
        PermissionCode.FINANCE_READ,
        PermissionCode.ANALYTICS_READ,
    },

    RoleName.WORKSHOP: {
        PermissionCode.USER_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.VEHICLE_READ,
        PermissionCode.INQUIRY_READ,
        # Inventory — can consume stock, cannot adjust counts
        PermissionCode.INVENTORY_READ,
        PermissionCode.INVENTORY_TRANSACT,
        PermissionCode.SUPPLIER_READ,
        # Projects — can update and cost, cannot approve
        PermissionCode.PROJECT_READ,
        PermissionCode.PROJECT_UPDATE,
        PermissionCode.PROJECT_COST,
        PermissionCode.EMPLOYEE_READ,
        PermissionCode.PRICING_READ,
        PermissionCode.FINANCE_READ,
        PermissionCode.ANALYTICS_READ,
    },

    RoleName.FINANCE: {
        PermissionCode.USER_READ,
        PermissionCode.AUDIT_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.VEHICLE_READ,
        PermissionCode.INQUIRY_READ,
        PermissionCode.INVENTORY_READ,
        PermissionCode.INVENTORY_PURCHASE,
        PermissionCode.SUPPLIER_READ,
        PermissionCode.SUPPLIER_WRITE,
        PermissionCode.PROJECT_READ,
        PermissionCode.PROJECT_COST,
        PermissionCode.EMPLOYEE_READ,
        PermissionCode.EMPLOYEE_WRITE,
        PermissionCode.PRICING_READ,
        PermissionCode.PRICING_WRITE,
        PermissionCode.FINANCE_READ,
        PermissionCode.INVOICE_WRITE,
        PermissionCode.PAYMENT_WRITE,
        PermissionCode.EXPENSE_WRITE,
        PermissionCode.FINANCE_REPORTS,
        PermissionCode.ANALYTICS_READ,
    },

    RoleName.VIEWER: {
        PermissionCode.USER_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.VEHICLE_READ,
        PermissionCode.INQUIRY_READ,
        PermissionCode.INVENTORY_READ,
        PermissionCode.SUPPLIER_READ,
        PermissionCode.PROJECT_READ,
        PermissionCode.EMPLOYEE_READ,
        PermissionCode.PRICING_READ,
        PermissionCode.FINANCE_READ,
        PermissionCode.FINANCE_REPORTS,
        PermissionCode.ANALYTICS_READ,
    },
}


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

SYSTEM_ROLE_NAMES: frozenset[str] = frozenset(
    r.value for r in RoleName
)


def default_permissions_for(role: RoleName | str) -> set[str]:
    """
    Return the default permission CODES (as strings) for a role.

    Returns an empty set for unknown roles. Normalizes RoleName → str
    so the result matches `Permission.code` column values directly.
    """
    key = role.value if isinstance(role, RoleName) else str(role)
    codes = DEFAULT_ROLE_PERMISSIONS.get(key, set())
    return {c.value if isinstance(c, PermissionCode) else str(c) for c in codes}


def is_system_role(role: RoleName | str) -> bool:
    """True for built-in roles seeded from DEFAULT_ROLE_PERMISSIONS."""
    key = role.value if isinstance(role, RoleName) else str(role)
    return key in SYSTEM_ROLE_NAMES