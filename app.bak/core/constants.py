from enum import StrEnum


class AppEnv(StrEnum):
    DEV = "development"
    STAGING = "staging"
    PROD = "production"
    TEST = "test"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PermissionCode(StrEnum):
    # Users
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # RBAC
    ROLE_READ = "role:read"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"

    # Audit
    AUDIT_READ = "audit:read"

    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"

    # Customers  ── NEW ──
    CUSTOMER_READ = "customer:read"
    CUSTOMER_WRITE = "customer:write"
    CUSTOMER_DELETE = "customer:delete"

    # Vehicles  ── NEW ──
    VEHICLE_READ = "vehicle:read"
    VEHICLE_WRITE = "vehicle:write"
    VEHICLE_DELETE = "vehicle:delete"


class RoleName(StrEnum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    SALES = "sales"
    WORKSHOP = "workshop"
    FINANCE = "finance"
    VIEWER = "viewer"


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VIEW = "VIEW"
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"