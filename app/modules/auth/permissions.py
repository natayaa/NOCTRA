# app/modules/auth/permissions.py
"""
Permission definitions and role-permission mapping.
"""

from typing import Dict, List, Set, Optional
from app.modules.auth.enums import UserRole, PermissionCategory, PermissionAction

# ==================== PERMISSION DEFINITIONS ====================

class Permissions:
    """Permission constants"""
    
    # ========== USER PERMISSIONS ==========
    USER_VIEW = "users:view"
    USER_CREATE = "users:create"
    USER_UPDATE = "users:update"
    USER_DELETE = "users:delete"
    USER_ROLES = "users:roles"
    
    # ========== AUTH PERMISSIONS ==========
    AUTH_LOGIN = "auth:login"
    AUTH_LOGOUT = "auth:logout"
    AUTH_REFRESH = "auth:refresh"
    AUTH_RESET = "auth:reset"
    AUTH_VERIFY = "auth:verify"
    AUTH_2FA = "auth:2fa"
    AUTH_SOCIAL = "auth:social"
    
    # ========== ORDER PERMISSIONS ==========
    ORDER_VIEW = "orders:view"
    ORDER_CREATE = "orders:create"
    ORDER_UPDATE = "orders:update"
    ORDER_DELETE = "orders:delete"
    ORDER_STATUS = "orders:status"
    ORDER_ASSIGN = "orders:assign"
    ORDER_APPROVE = "orders:approve"
    ORDER_REJECT = "orders:reject"
    
    # ========== INVENTORY PERMISSIONS ==========
    INVENTORY_VIEW = "inventory:view"
    INVENTORY_CREATE = "inventory:create"
    INVENTORY_UPDATE = "inventory:update"
    INVENTORY_DELETE = "inventory:delete"
    INVENTORY_STOCK = "inventory:stock"
    INVENTORY_ADJUST = "inventory:adjust"
    INVENTORY_TRANSFER = "inventory:transfer"
    
    # ========== CUSTOMER PERMISSIONS ==========
    CUSTOMER_VIEW = "customers:view"
    CUSTOMER_CREATE = "customers:create"
    CUSTOMER_UPDATE = "customers:update"
    CUSTOMER_DELETE = "customers:delete"
    
    # ========== REPORT PERMISSIONS ==========
    REPORT_VIEW = "reports:view"
    REPORT_GENERATE = "reports:generate"
    REPORT_EXPORT = "reports:export"
    REPORT_SCHEDULE = "reports:schedule"
    
    # ========== SETTINGS PERMISSIONS ==========
    SETTINGS_VIEW = "settings:view"
    SETTINGS_UPDATE = "settings:update"
    SETTINGS_SYSTEM = "settings:system"
    
    # ========== WORKSHOP PERMISSIONS ==========
    WORKSHOP_VIEW = "workshop:view"
    WORKSHOP_MANAGE = "workshop:manage"
    WORKSHOP_SCHEDULE = "workshop:schedule"
    WORKSHOP_EQUIPMENT = "workshop:equipment"
    
    # ========== FINANCE PERMISSIONS ==========
    FINANCE_VIEW = "finance:view"
    FINANCE_MANAGE = "finance:manage"
    FINANCE_INVOICE = "finance:invoice"
    FINANCE_PAYMENT = "finance:payment"
    FINANCE_REPORT = "finance:report"

# ==================== PERMISSION METADATA ====================

PERMISSION_METADATA: Dict[str, Dict] = {
    # User permissions
    Permissions.USER_VIEW: {
        "category": PermissionCategory.USER,
        "action": PermissionAction.VIEW,
        "description": "View user information",
    },
    Permissions.USER_CREATE: {
        "category": PermissionCategory.USER,
        "action": PermissionAction.CREATE,
        "description": "Create new users",
    },
    Permissions.USER_UPDATE: {
        "category": PermissionCategory.USER,
        "action": PermissionAction.UPDATE,
        "description": "Update user information",
    },
    Permissions.USER_DELETE: {
        "category": PermissionCategory.USER,
        "action": PermissionAction.DELETE,
        "description": "Delete users",
    },
    Permissions.USER_ROLES: {
        "category": PermissionCategory.USER,
        "action": PermissionAction.MANAGE,
        "description": "Manage user roles and permissions",
    },
    
    # Auth permissions
    Permissions.AUTH_LOGIN: {
        "category": PermissionCategory.AUTH,
        "action": PermissionAction.VIEW,
        "description": "Login to the system",
    },
    Permissions.AUTH_LOGOUT: {
        "category": PermissionCategory.AUTH,
        "action": PermissionAction.VIEW,
        "description": "Logout from the system",
    },
    Permissions.AUTH_REFRESH: {
        "category": PermissionCategory.AUTH,
        "action": PermissionAction.VIEW,
        "description": "Refresh authentication token",
    },
    Permissions.AUTH_RESET: {
        "category": PermissionCategory.AUTH,
        "action": PermissionAction.UPDATE,
        "description": "Reset password",
    },
    Permissions.AUTH_VERIFY: {
        "category": PermissionCategory.AUTH,
        "action": PermissionAction.VIEW,
        "description": "Verify email or phone",
    },
    Permissions.AUTH_2FA: {
        "category": PermissionCategory.AUTH,
        "action": PermissionAction.MANAGE,
        "description": "Manage two-factor authentication",
    },
    Permissions.AUTH_SOCIAL: {
        "category": PermissionCategory.AUTH,
        "action": PermissionAction.MANAGE,
        "description": "Manage social authentication",
    },
    
    # Order permissions
    Permissions.ORDER_VIEW: {
        "category": PermissionCategory.ORDER,
        "action": PermissionAction.VIEW,
        "description": "View orders",
    },
    Permissions.ORDER_CREATE: {
        "category": PermissionCategory.ORDER,
        "action": PermissionAction.CREATE,
        "description": "Create new orders",
    },
    Permissions.ORDER_UPDATE: {
        "category": PermissionCategory.ORDER,
        "action": PermissionAction.UPDATE,
        "description": "Update orders",
    },
    Permissions.ORDER_DELETE: {
        "category": PermissionCategory.ORDER,
        "action": PermissionAction.DELETE,
        "description": "Delete orders",
    },
    Permissions.ORDER_STATUS: {
        "category": PermissionCategory.ORDER,
        "action": PermissionAction.MANAGE,
        "description": "Change order status",
    },
    Permissions.ORDER_ASSIGN: {
        "category": PermissionCategory.ORDER,
        "action": PermissionAction.UPDATE,
        "description": "Assign orders to staff",
    },
    Permissions.ORDER_APPROVE: {
        "category": PermissionCategory.ORDER,
        "action": PermissionAction.APPROVE,
        "description": "Approve orders",
    },
    Permissions.ORDER_REJECT: {
        "category": PermissionCategory.ORDER,
        "action": PermissionAction.REJECT,
        "description": "Reject orders",
    },
    
    # Inventory permissions
    Permissions.INVENTORY_VIEW: {
        "category": PermissionCategory.INVENTORY,
        "action": PermissionAction.VIEW,
        "description": "View inventory items",
    },
    Permissions.INVENTORY_CREATE: {
        "category": PermissionCategory.INVENTORY,
        "action": PermissionAction.CREATE,
        "description": "Create inventory items",
    },
    Permissions.INVENTORY_UPDATE: {
        "category": PermissionCategory.INVENTORY,
        "action": PermissionAction.UPDATE,
        "description": "Update inventory items",
    },
    Permissions.INVENTORY_DELETE: {
        "category": PermissionCategory.INVENTORY,
        "action": PermissionAction.DELETE,
        "description": "Delete inventory items",
    },
    Permissions.INVENTORY_STOCK: {
        "category": PermissionCategory.INVENTORY,
        "action": PermissionAction.MANAGE,
        "description": "Manage stock levels",
    },
    Permissions.INVENTORY_ADJUST: {
        "category": PermissionCategory.INVENTORY,
        "action": PermissionAction.UPDATE,
        "description": "Adjust inventory quantities",
    },
    Permissions.INVENTORY_TRANSFER: {
        "category": PermissionCategory.INVENTORY,
        "action": PermissionAction.MANAGE,
        "description": "Transfer inventory between locations",
    },
    
    # Customer permissions
    Permissions.CUSTOMER_VIEW: {
        "category": PermissionCategory.CUSTOMER,
        "action": PermissionAction.VIEW,
        "description": "View customer information",
    },
    Permissions.CUSTOMER_CREATE: {
        "category": PermissionCategory.CUSTOMER,
        "action": PermissionAction.CREATE,
        "description": "Create new customers",
    },
    Permissions.CUSTOMER_UPDATE: {
        "category": PermissionCategory.CUSTOMER,
        "action": PermissionAction.UPDATE,
        "description": "Update customer information",
    },
    Permissions.CUSTOMER_DELETE: {
        "category": PermissionCategory.CUSTOMER,
        "action": PermissionAction.DELETE,
        "description": "Delete customers",
    },
    
    # Report permissions
    Permissions.REPORT_VIEW: {
        "category": PermissionCategory.REPORT,
        "action": PermissionAction.VIEW,
        "description": "View reports",
    },
    Permissions.REPORT_GENERATE: {
        "category": PermissionCategory.REPORT,
        "action": PermissionAction.CREATE,
        "description": "Generate reports",
    },
    Permissions.REPORT_EXPORT: {
        "category": PermissionCategory.REPORT,
        "action": PermissionAction.EXPORT,
        "description": "Export reports",
    },
    Permissions.REPORT_SCHEDULE: {
        "category": PermissionCategory.REPORT,
        "action": PermissionAction.MANAGE,
        "description": "Schedule reports",
    },
    
    # Settings permissions
    Permissions.SETTINGS_VIEW: {
        "category": PermissionCategory.SETTINGS,
        "action": PermissionAction.VIEW,
        "description": "View system settings",
    },
    Permissions.SETTINGS_UPDATE: {
        "category": PermissionCategory.SETTINGS,
        "action": PermissionAction.UPDATE,
        "description": "Update system settings",
    },
    Permissions.SETTINGS_SYSTEM: {
        "category": PermissionCategory.SETTINGS,
        "action": PermissionAction.MANAGE,
        "description": "Manage system configuration",
    },
    
    # Workshop permissions
    Permissions.WORKSHOP_VIEW: {
        "category": PermissionCategory.WORKSHOP,
        "action": PermissionAction.VIEW,
        "description": "View workshop information",
    },
    Permissions.WORKSHOP_MANAGE: {
        "category": PermissionCategory.WORKSHOP,
        "action": PermissionAction.MANAGE,
        "description": "Manage workshop operations",
    },
    Permissions.WORKSHOP_SCHEDULE: {
        "category": PermissionCategory.WORKSHOP,
        "action": PermissionAction.MANAGE,
        "description": "Manage workshop schedule",
    },
    Permissions.WORKSHOP_EQUIPMENT: {
        "category": PermissionCategory.WORKSHOP,
        "action": PermissionAction.MANAGE,
        "description": "Manage workshop equipment",
    },
    
    # Finance permissions
    Permissions.FINANCE_VIEW: {
        "category": PermissionCategory.FINANCE,
        "action": PermissionAction.VIEW,
        "description": "View financial information",
    },
    Permissions.FINANCE_MANAGE: {
        "category": PermissionCategory.FINANCE,
        "action": PermissionAction.MANAGE,
        "description": "Manage financial operations",
    },
    Permissions.FINANCE_INVOICE: {
        "category": PermissionCategory.FINANCE,
        "action": PermissionAction.MANAGE,
        "description": "Manage invoices",
    },
    Permissions.FINANCE_PAYMENT: {
        "category": PermissionCategory.FINANCE,
        "action": PermissionAction.MANAGE,
        "description": "Manage payments",
    },
    Permissions.FINANCE_REPORT: {
        "category": PermissionCategory.FINANCE,
        "action": PermissionAction.VIEW,
        "description": "View financial reports",
    },
}

# ==================== ROLE PERMISSION MAPPING ====================

ROLE_PERMISSIONS: Dict[UserRole, List[str]] = {
    # Admin has all permissions
    UserRole.ADMIN: [
                        getattr(Permissions, attr) 
                        for attr in dir(Permissions) 
                        if not attr.startswith('_') 
                        and not callable(getattr(Permissions, attr))
                        and isinstance(getattr(Permissions, attr), str)
                    ],
    
    # Manager has most permissions
    UserRole.MANAGER: [
        # User management
        Permissions.USER_VIEW,
        Permissions.USER_CREATE,
        Permissions.USER_UPDATE,
        # Auth
        Permissions.AUTH_LOGIN,
        Permissions.AUTH_LOGOUT,
        Permissions.AUTH_REFRESH,
        # Orders
        Permissions.ORDER_VIEW,
        Permissions.ORDER_CREATE,
        Permissions.ORDER_UPDATE,
        Permissions.ORDER_STATUS,
        Permissions.ORDER_ASSIGN,
        Permissions.ORDER_APPROVE,
        Permissions.ORDER_REJECT,
        # Inventory
        Permissions.INVENTORY_VIEW,
        Permissions.INVENTORY_CREATE,
        Permissions.INVENTORY_UPDATE,
        Permissions.INVENTORY_STOCK,
        Permissions.INVENTORY_ADJUST,
        Permissions.INVENTORY_TRANSFER,
        # Customers
        Permissions.CUSTOMER_VIEW,
        Permissions.CUSTOMER_CREATE,
        Permissions.CUSTOMER_UPDATE,
        # Reports
        Permissions.REPORT_VIEW,
        Permissions.REPORT_GENERATE,
        Permissions.REPORT_EXPORT,
        # Workshop
        Permissions.WORKSHOP_VIEW,
        Permissions.WORKSHOP_MANAGE,
        Permissions.WORKSHOP_SCHEDULE,
        # Finance
        Permissions.FINANCE_VIEW,
        Permissions.FINANCE_INVOICE,
        Permissions.FINANCE_PAYMENT,
        Permissions.FINANCE_REPORT,
    ],
    
    # Staff has limited permissions
    UserRole.STAFF: [
        # Auth
        Permissions.AUTH_LOGIN,
        Permissions.AUTH_LOGOUT,
        Permissions.AUTH_REFRESH,
        # Orders
        Permissions.ORDER_VIEW,
        Permissions.ORDER_CREATE,
        Permissions.ORDER_UPDATE,
        Permissions.ORDER_STATUS,
        # Inventory
        Permissions.INVENTORY_VIEW,
        Permissions.INVENTORY_UPDATE,
        Permissions.INVENTORY_STOCK,
        # Customers
        Permissions.CUSTOMER_VIEW,
        Permissions.CUSTOMER_CREATE,
        Permissions.CUSTOMER_UPDATE,
        # Reports
        Permissions.REPORT_VIEW,
        # Workshop
        Permissions.WORKSHOP_VIEW,
        # Finance
        Permissions.FINANCE_VIEW,
    ],
    
    # Mechanic has workshop-specific permissions
    UserRole.MECHANIC: [
        # Auth
        Permissions.AUTH_LOGIN,
        Permissions.AUTH_LOGOUT,
        Permissions.AUTH_REFRESH,
        # Orders
        Permissions.ORDER_VIEW,
        Permissions.ORDER_STATUS,
        # Inventory
        Permissions.INVENTORY_VIEW,
        # Workshop
        Permissions.WORKSHOP_VIEW,
        Permissions.WORKSHOP_MANAGE,
        Permissions.WORKSHOP_SCHEDULE,
        Permissions.WORKSHOP_EQUIPMENT,
        # Customers
        Permissions.CUSTOMER_VIEW,
    ],
    
    # Customer has minimal permissions
    UserRole.CUSTOMER: [
        # Auth
        Permissions.AUTH_LOGIN,
        Permissions.AUTH_LOGOUT,
        Permissions.AUTH_REFRESH,
        Permissions.AUTH_RESET,
        Permissions.AUTH_VERIFY,
        # Orders (only their own)
        Permissions.ORDER_VIEW,
        Permissions.ORDER_CREATE,
        # Customers (only their own)
        Permissions.CUSTOMER_VIEW,
        Permissions.CUSTOMER_UPDATE,
    ],
    
    # Guest has view-only permissions
    UserRole.GUEST: [
        # Auth
        Permissions.AUTH_LOGIN,
        Permissions.AUTH_RESET,
        # Orders (view only)
        Permissions.ORDER_VIEW,
        # Customers (view only)
        Permissions.CUSTOMER_VIEW,
    ],
}

# ==================== PERMISSION HELPERS ====================

def get_permission_metadata(permission: str) -> Optional[Dict]:
    """Get metadata for a permission"""
    return PERMISSION_METADATA.get(permission)

def get_permission_category(permission: str) -> Optional[PermissionCategory]:
    """Get category for a permission"""
    metadata = get_permission_metadata(permission)
    return metadata.get("category") if metadata else None

def get_permission_action(permission: str) -> Optional[PermissionAction]:
    """Get action for a permission"""
    metadata = get_permission_metadata(permission)
    return metadata.get("action") if metadata else None

def get_permission_description(permission: str) -> Optional[str]:
    """Get description for a permission"""
    metadata = get_permission_metadata(permission)
    return metadata.get("description") if metadata else None

def get_permissions_by_category(category: PermissionCategory) -> List[str]:
    """Get all permissions in a category"""
    return [
        perm for perm, meta in PERMISSION_METADATA.items()
        if meta.get("category") == category
    ]

def get_permissions_by_action(action: PermissionAction) -> List[str]:
    """Get all permissions with a specific action"""
    return [
        perm for perm, meta in PERMISSION_METADATA.items()
        if meta.get("action") == action
    ]

def get_role_permissions(role: UserRole) -> List[str]:
    """Get all permissions for a role"""
    return ROLE_PERMISSIONS.get(role, [])

def has_permission(role: UserRole, permission: str) -> bool:
    """Check if a role has a specific permission"""
    return permission in get_role_permissions(role)

def has_any_permission(role: UserRole, permissions: List[str]) -> bool:
    """Check if a role has any of the given permissions"""
    role_perms = set(get_role_permissions(role))
    return bool(role_perms.intersection(set(permissions)))

def has_all_permissions(role: UserRole, permissions: List[str]) -> bool:
    """Check if a role has all of the given permissions"""
    role_perms = set(get_role_permissions(role))
    return set(permissions).issubset(role_perms)

# ==================== EXPORTS ====================

__all__ = [
    'Permissions',
    'PERMISSION_METADATA',
    'ROLE_PERMISSIONS',
    'get_permission_metadata',
    'get_permission_category',
    'get_permission_action',
    'get_permission_description',
    'get_permissions_by_category',
    'get_permissions_by_action',
    'get_role_permissions',
    'has_permission',
    'has_any_permission',
    'has_all_permissions',
]