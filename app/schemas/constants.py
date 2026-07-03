# schemas/constants.py
from enum import Enum


class InquiryStatus(str, Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    APPROVED = "approved"  # <-- TAMBAHKAN INI
    CONVERTED = "converted"
    REJECTED = "rejected"
    CLOSED = "closed"
    COMPLETED = "completed"


class ProjectStatus(str, Enum):
    """Status untuk project."""
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectPriority(str, Enum):
    """Priority untuk project."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


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


class InventoryStatus(str, Enum):
    """Status inventory item."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"
    OUT_OF_STOCK = "out_of_stock"
    ON_ORDER = "on_order"


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


class PriceListCategory(str, Enum):
    """Kategori price list."""
    SERVICE = "service"
    MATERIAL = "material"
    LABOR = "labor"
    BIKE_MODEL = "bike_model"
    PAINT = "paint"
    FINISH = "finish"
    ACCESSORY = "accessory"