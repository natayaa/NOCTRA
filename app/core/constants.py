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

    # Inquiries  ── NEW ──
    INQUIRY_READ = "inquiry:read"
    INQUIRY_CREATE = "inquiry:create"
    INQUIRY_UPDATE = "inquiry:update"
    INQUIRY_ASSIGN = "inquiry:assign"
    INQUIRY_CLOSE = "inquiry:close" 

    # Inventory  ── NEW (Phase 3) ──
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"
    INVENTORY_TRANSACT = "inventory:transact"
    INVENTORY_ADJUST = "inventory:adjust"
    INVENTORY_PURCHASE = "inventory:purchase"

    # Suppliers  ── NEW (Phase 3) ──
    SUPPLIER_READ = "supplier:read"
    SUPPLIER_WRITE = "supplier:write"

    # Projects (Phase 4)
    PROJECT_READ = "project:read"
    PROJECT_CREATE = "project:create"
    PROJECT_UPDATE = "project:update"
    PROJECT_COST = "project:cost"           # enter/change cost items
    PROJECT_APPROVE = "project:approve"     # approve quote / advance status
    PROJECT_DELETE = "project:delete"

    # Employees (Phase 4)
    EMPLOYEE_READ = "employee:read"
    EMPLOYEE_WRITE = "employee:write"

    # Phase 5
    PRICING_READ = "pricing:read"
    PRICING_WRITE = "pricing:write"

    # Finance (Phase 6)
    FINANCE_READ = "finance:read"
    INVOICE_WRITE = "invoice:write"
    PAYMENT_WRITE = "payment:write"
    EXPENSE_WRITE = "expense:write"
    FINANCE_REPORTS = "finance:reports"

    # Analytics (Phase 7)
    ANALYTICS_READ = "analytics:read"


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
    # Phase 2b — workflow actions
    ASSIGN = "ASSIGN"
    STATUS_CHANGE = "STATUS_CHANGE"
    # Phase 3
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    PRICE_CHANGE = "PRICE_CHANGE"

    # Inventory
    INVENTORY_READ = "inventory:read"
    INVENTORY_WRITE = "inventory:write"          # create/edit materials, suppliers
    INVENTORY_TRANSACT = "inventory:transact"    # record stock movements
    INVENTORY_ADJUST = "inventory:adjust"        # adjustments + waste
    INVENTORY_PURCHASE = "inventory:purchase"    # manage purchase orders

    # Suppliers (separate for fine-grained control)
    SUPPLIER_READ = "supplier:read"
    SUPPLIER_WRITE = "supplier:write"

    # Phase 4
    COST_ENTRY = "COST_ENTRY"
    PROJECT_APPROVED = "PROJECT_APPROVED"
    PROJECT_COMPLETED = "PROJECT_COMPLETED"

    # Phase 6
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    PAYMENT_MADE = "PAYMENT_MADE"
    INVOICE_SENT = "INVOICE_SENT"
    EXPENSE_RECORDED = "EXPENSE_RECORDED"