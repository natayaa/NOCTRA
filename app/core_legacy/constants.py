# core/constants.py
from enum import Enum


# =============================================================================
# Inquiry Status
# =============================================================================

class InquiryStatus(str, Enum):
    """Status inquiry."""
    NEW = "new"
    UNDER_REVIEW = "under_review"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    APPROVED = "approved"
    CONVERTED = "converted"
    REJECTED = "rejected"
    CLOSED = "closed"
    COMPLETED = "completed"


# =============================================================================
# Project Status
# =============================================================================

class ProjectStatus(str, Enum):
    """Status project."""
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NEW = "new"


class ProjectPriority(str, Enum):
    """Priority project."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# =============================================================================
# Payment
# =============================================================================

class PaymentType(str, Enum):
    """Tipe pembayaran."""
    DEPOSIT = "deposit"
    PAYMENT = "payment"
    REFUND = "refund"
    INSTALLMENT = "installment"


class PaymentStatus(str, Enum):
    """Status pembayaran."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIAL = "partial"


class PaymentMethod(str, Enum):
    """Metode pembayaran."""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    E_WALLET = "e_wallet"
    QRIS = "qris"
    OTHER = "other"


# =============================================================================
# Invoice
# =============================================================================

class InvoiceStatus(str, Enum):
    """Status invoice."""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# =============================================================================
# Inventory
# =============================================================================

class InventoryStatus(str, Enum):
    """Status inventory item."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"
    OUT_OF_STOCK = "out_of_stock"
    ON_ORDER = "on_order"
    LOW_STOCK = "low_stock"


class StockMovementType(str, Enum):
    """Tipe pergerakan stock."""
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"
    ADJUSTMENT = "adjustment"
    USAGE = "usage"
    TRANSFER = "transfer"
    WASTE = "waste"
    RECEIVED = "received"
    SHIPPED = "shipped"
    RESERVATION = "reservation"
    RELEASE = "release"


# =============================================================================
# Expense
# =============================================================================

class ExpenseCategory(str, Enum):
    """Kategori expense."""
    MATERIALS = "materials"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    RENTAL = "rental"
    TRANSPORTATION = "transportation"
    UTILITIES = "utilities"
    MARKETING = "marketing"
    ADMINISTRATIVE = "administrative"
    OTHER = "other"


class ExpenseStatus(str, Enum):
    """Status expense."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    CANCELLED = "cancelled"


# =============================================================================
# Price List
# =============================================================================

class PriceListCategory(str, Enum):
    """Kategori price list."""
    SERVICE = "service"
    MATERIAL = "material"
    LABOR = "labor"
    BIKE_MODEL = "bike_model"
    PAINT = "paint"
    FINISH = "finish"
    ACCESSORY = "accessory"


# =============================================================================
# Notification
# =============================================================================

class NotificationType(str, Enum):
    """Tipe notifikasi."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, Enum):
    """Status notifikasi."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"

# core/constants.py - TAMBAHAN DI AKHIR FILE

# ============================================================================
# User Status
# ============================================================================


class UserStatus(str, Enum):
    """Status user."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"


# ============================================================================
# User Role (Enum untuk reference)
# ============================================================================

class UserRole(str, Enum):
    """Default user roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    SUPERVISOR = "supervisor"
    TECHNICIAN = "technician"
    USER = "user"


# ============================================================================
# Default Roles & Permissions Configuration
# ============================================================================

DEFAULT_ROLES = {
    "admin": {
        "display_name": "Administrator",
        "description": "Full access to all features",
        "is_system": True,
        "permissions": ["*:*"]  # All permissions
    },
    "manager": {
        "display_name": "Project Manager",
        "description": "Manage projects and teams",
        "is_system": True,
        "permissions": [
            "project:*",
            "inquiry:*",
            "payment:view",
            "payment:create",
            "invoice:view",
            "invoice:create",
            "inventory:view",
            "user:view"
        ]
    },
    "supervisor": {
        "display_name": "Supervisor",
        "description": "Supervise projects and quality",
        "is_system": True,
        "permissions": [
            "project:view",
            "project:update",
            "project:complete",
            "inquiry:view",
            "inquiry:update",
            "payment:view",
            "invoice:view",
            "inventory:view",
            "report:view"
        ]
    },
    "technician": {
        "display_name": "Technician",
        "description": "Execute tasks and log work",
        "is_system": True,
        "permissions": [
            "project:view",
            "task:view",
            "task:update",
            "task:complete",
            "labor:view",
            "labor:create",
            "inventory:view",
            "profile:read",
            "profile:update"
        ]
    },
    "user": {
        "display_name": "User",
        "description": "Basic user access",
        "is_system": True,
        "permissions": [
            "profile:read",
            "profile:update",
            "dashboard:view",
            "inquiry:create"
        ]
    }
}


# ============================================================================
# Default Permissions List
# ============================================================================

DEFAULT_PERMISSIONS = [
    # Project
    {"name": "project:view", "display_name": "View Projects",
        "module": "project", "action": "view"},
    {"name": "project:create", "display_name": "Create Projects",
        "module": "project", "action": "create"},
    {"name": "project:update", "display_name": "Update Projects",
        "module": "project", "action": "update"},
    {"name": "project:delete", "display_name": "Delete Projects",
        "module": "project", "action": "delete"},
    {"name": "project:complete", "display_name": "Complete Projects",
        "module": "project", "action": "complete"},
    {"name": "project:manage", "display_name": "Manage Projects",
        "module": "project", "action": "manage"},

    # Inquiry
    {"name": "inquiry:view", "display_name": "View Inquiries",
        "module": "inquiry", "action": "view"},
    {"name": "inquiry:create", "display_name": "Create Inquiries",
        "module": "inquiry", "action": "create"},
    {"name": "inquiry:update", "display_name": "Update Inquiries",
        "module": "inquiry", "action": "update"},
    {"name": "inquiry:delete", "display_name": "Delete Inquiries",
        "module": "inquiry", "action": "delete"},
    {"name": "inquiry:convert", "display_name": "Convert Inquiries",
        "module": "inquiry", "action": "convert"},
    {"name": "inquiry:manage", "display_name": "Manage Inquiries",
        "module": "inquiry", "action": "manage"},

    # Payment
    {"name": "payment:view", "display_name": "View Payments",
        "module": "payment", "action": "view"},
    {"name": "payment:create", "display_name": "Create Payments",
        "module": "payment", "action": "create"},
    {"name": "payment:update", "display_name": "Update Payments",
        "module": "payment", "action": "update"},
    {"name": "payment:delete", "display_name": "Delete Payments",
        "module": "payment", "action": "delete"},
    {"name": "payment:manage", "display_name": "Manage Payments",
        "module": "payment", "action": "manage"},

    # Invoice
    {"name": "invoice:view", "display_name": "View Invoices",
        "module": "invoice", "action": "view"},
    {"name": "invoice:create", "display_name": "Create Invoices",
        "module": "invoice", "action": "create"},
    {"name": "invoice:update", "display_name": "Update Invoices",
        "module": "invoice", "action": "update"},
    {"name": "invoice:delete", "display_name": "Delete Invoices",
        "module": "invoice", "action": "delete"},
    {"name": "invoice:manage", "display_name": "Manage Invoices",
        "module": "invoice", "action": "manage"},

    # Inventory
    {"name": "inventory:view", "display_name": "View Inventory",
        "module": "inventory", "action": "view"},
    {"name": "inventory:create", "display_name": "Create Inventory",
        "module": "inventory", "action": "create"},
    {"name": "inventory:update", "display_name": "Update Inventory",
        "module": "inventory", "action": "update"},
    {"name": "inventory:delete", "display_name": "Delete Inventory",
        "module": "inventory", "action": "delete"},
    {"name": "inventory:manage", "display_name": "Manage Inventory",
        "module": "inventory", "action": "manage"},

    # Task
    {"name": "task:view", "display_name": "View Tasks",
        "module": "task", "action": "view"},
    {"name": "task:create", "display_name": "Create Tasks",
        "module": "task", "action": "create"},
    {"name": "task:update", "display_name": "Update Tasks",
        "module": "task", "action": "update"},
    {"name": "task:delete", "display_name": "Delete Tasks",
        "module": "task", "action": "delete"},
    {"name": "task:complete", "display_name": "Complete Tasks",
        "module": "task", "action": "complete"},

    # Labor
    {"name": "labor:view", "display_name": "View Labor",
        "module": "labor", "action": "view"},
    {"name": "labor:create", "display_name": "Create Labor",
        "module": "labor", "action": "create"},
    {"name": "labor:update", "display_name": "Update Labor",
        "module": "labor", "action": "update"},
    {"name": "labor:delete", "display_name": "Delete Labor",
        "module": "labor", "action": "delete"},

    # Report
    {"name": "report:view", "display_name": "View Reports",
        "module": "report", "action": "view"},
    {"name": "report:create", "display_name": "Create Reports",
        "module": "report", "action": "create"},
    {"name": "report:export", "display_name": "Export Reports",
        "module": "report", "action": "export"},

    # Profile
    {"name": "profile:read", "display_name": "Read Profile",
        "module": "profile", "action": "read"},
    {"name": "profile:update", "display_name": "Update Profile",
        "module": "profile", "action": "update"},

    # Dashboard
    {"name": "dashboard:view", "display_name": "View Dashboard",
        "module": "dashboard", "action": "view"},

    # User Management
    {"name": "user:view", "display_name": "View Users",
        "module": "user", "action": "view"},
    {"name": "user:create", "display_name": "Create Users",
        "module": "user", "action": "create"},
    {"name": "user:update", "display_name": "Update Users",
        "module": "user", "action": "update"},
    {"name": "user:delete", "display_name": "Delete Users",
        "module": "user", "action": "delete"},
    {"name": "user:manage", "display_name": "Manage Users",
        "module": "user", "action": "manage"},

    # Role Management
    {"name": "role:view", "display_name": "View Roles",
        "module": "role", "action": "view"},
    {"name": "role:create", "display_name": "Create Roles",
        "module": "role", "action": "create"},
    {"name": "role:update", "display_name": "Update Roles",
        "module": "role", "action": "update"},
    {"name": "role:delete", "display_name": "Delete Roles",
        "module": "role", "action": "delete"},
    {"name": "role:manage", "display_name": "Manage Roles",
        "module": "role", "action": "manage"},
]
