from app.core.constants import PermissionCode, RoleName

DEFAULT_ROLE_PERMISSIONS: dict[str, set[PermissionCode]] = {
    RoleName.SUPERUSER: set(PermissionCode),

    RoleName.ADMIN: {
        # ... existing Phase 1 permissions ...
        PermissionCode.USER_READ,
        PermissionCode.USER_CREATE,
        PermissionCode.USER_UPDATE,
        PermissionCode.ROLE_READ,
        PermissionCode.AUDIT_READ,
        PermissionCode.SETTINGS_READ,
        PermissionCode.SETTINGS_UPDATE,
        # Phase 2a
        PermissionCode.CUSTOMER_READ,
        PermissionCode.CUSTOMER_WRITE,
        PermissionCode.CUSTOMER_DELETE,
        PermissionCode.VEHICLE_READ,
        PermissionCode.VEHICLE_WRITE,
        PermissionCode.VEHICLE_DELETE,
        # Phase 2b
        PermissionCode.INQUIRY_READ,
        PermissionCode.INQUIRY_CREATE,
        PermissionCode.INQUIRY_UPDATE,
        PermissionCode.INQUIRY_ASSIGN,
        PermissionCode.INQUIRY_CLOSE,
        # Phase 3
        PermissionCode.INVENTORY_READ,
        PermissionCode.INVENTORY_WRITE,
        PermissionCode.INVENTORY_TRANSACT,
        PermissionCode.INVENTORY_ADJUST,
        PermissionCode.INVENTORY_PURCHASE,
        PermissionCode.SUPPLIER_READ,
        PermissionCode.SUPPLIER_WRITE,
        # Phase 4
        PermissionCode.PROJECT_READ,
        PermissionCode.PROJECT_CREATE,
        PermissionCode.PROJECT_UPDATE,
        PermissionCode.PROJECT_COST,
        PermissionCode.PROJECT_APPROVE,
        PermissionCode.PROJECT_DELETE,
        PermissionCode.EMPLOYEE_READ,
        PermissionCode.EMPLOYEE_WRITE,
        # Phase 5
        PermissionCode.PRICING_READ,
        PermissionCode.PRICING_WRITE,

        # Phase 6
        PermissionCode.FINANCE_READ,
        PermissionCode.INVOICE_WRITE,
        PermissionCode.PAYMENT_WRITE,
        PermissionCode.EXPENSE_WRITE,
        PermissionCode.FINANCE_REPORTS,

        PermissionCode.ANALYTICS_READ,
    },

    RoleName.SALES: {
        PermissionCode.USER_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.CUSTOMER_WRITE,
        PermissionCode.VEHICLE_READ,
        PermissionCode.VEHICLE_WRITE,
        # Phase 2b — sales owns the inquiry pipeline
        PermissionCode.INQUIRY_READ,
        PermissionCode.INQUIRY_CREATE,
        PermissionCode.INQUIRY_UPDATE,
        PermissionCode.INQUIRY_ASSIGN,
        PermissionCode.INQUIRY_CLOSE,
        # Phase 3
        PermissionCode.INVENTORY_READ,
        PermissionCode.SUPPLIER_READ,
        # Phase 4
        PermissionCode.PROJECT_READ,
        PermissionCode.PROJECT_CREATE,
        PermissionCode.PROJECT_UPDATE,
        PermissionCode.PROJECT_APPROVE,
        PermissionCode.EMPLOYEE_READ,
        # Phase 5
        PermissionCode.PRICING_READ,
        # Phase 6
        PermissionCode.FINANCE_READ, 
        # Phase 7
        PermissionCode.ANALYTICS_READ,
    },

    RoleName.WORKSHOP: {
        PermissionCode.USER_READ,
        PermissionCode.CUSTOMER_READ,
        PermissionCode.VEHICLE_READ,
        # Workshop can read inquiries but not mutate them
        PermissionCode.INQUIRY_READ,
        PermissionCode.INVENTORY_READ,
        PermissionCode.INVENTORY_TRANSACT,       # painters consume stock
        PermissionCode.SUPPLIER_READ,
        # Phase 4
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