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

    # Customers
    CUSTOMER_READ = "customer:read"
    CUSTOMER_WRITE = "customer:write"
    CUSTOMER_DELETE = "customer:delete"

    # Vehicles
    VEHICLE_READ = "vehicle:read"
    VEHICLE_WRITE = "vehicle:write"
    VEHICLE_DELETE = "vehicle:delete"

    # Inquiries
    INQUIRY_READ = "inquiry:read"
    INQUIRY_CREATE = "inquiry:create"
    INQUIRY_UPDATE = "inquiry:update"
    INQUIRY_ASSIGN = "inquiry:assign"
    INQUIRY_CLOSE = "inquiry:close"

    # Inventory
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"
    INVENTORY_TRANSACT = "inventory:transact"
    INVENTORY_ADJUST = "inventory:adjust"
    INVENTORY_PURCHASE = "inventory:purchase"

    # Suppliers
    SUPPLIER_READ = "supplier:read"
    SUPPLIER_WRITE = "supplier:write"

    # Projects
    PROJECT_READ = "project:read"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_COST = "project:cost"
    PROJECT_APPROVE = "project:approve"
    PROJECT_DELETE = "project:delete"

    # Employees
    EMPLOYEE_READ = "employee:read"
    EMPLOYEE_WRITE = "employee:write"

    # Pricing
    PRICING_READ = "pricing:read"
    PRICING_WRITE = "pricing:write"

    # Finance
    FINANCE_READ = "finance:read"
    INVOICE_WRITE = "invoice:write"
    PAYMENT_WRITE = "payment:write"
    EXPENSE_WRITE = "expense:write"
    FINANCE_REPORTS = "finance:reports"

    # Analytics
    ANALYTICS_READ = "analytics:read"


class RoleName(StrEnum):
    SUPERUSER = "superuser"
    ADMIN = "admin"
    SALES = "sales"
    WORKSHOP = "workshop"
    FINANCE = "finance"
    VIEWER = "viewer"


class AuditAction(StrEnum):
    # CRUD
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VIEW = "VIEW"

    # Auth
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    REFRESH = "REFRESH"  # addition
    PASSWORD_RESET = "PASSWORD_RESET"

    # System
    EXPORT = "EXPORT"

    # Workflow
    ASSIGN = "ASSIGN"
    STATUS_CHANGE = "STATUS_CHANGE"

    # Inventory
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    PRICE_CHANGE = "PRICE_CHANGE"

    # Projects
    COST_ENTRY = "COST_ENTRY"
    PROJECT_APPROVED = "PROJECT_APPROVED"
    PROJECT_COMPLETED = "PROJECT_COMPLETED"

    # Finance
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    PAYMENT_MADE = "PAYMENT_MADE"
    INVOICE_SENT = "INVOICE_SENT"
    EXPENSE_RECORDED = "EXPENSE_RECORDED"