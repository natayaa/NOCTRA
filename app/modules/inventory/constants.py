"""Inventory vocabulary: material categories, transaction types, units."""

from __future__ import annotations

from enum import StrEnum


# ════════════════════════════════════════════════════════════════
# MATERIALS
# ════════════════════════════════════════════════════════════════

class MaterialCategory(StrEnum):
    PRIMER = "PRIMER"
    BASECOAT = "BASECOAT"
    CLEARCOAT = "CLEARCOAT"
    THINNER = "THINNER"
    CHEMICAL = "CHEMICAL"          # hardeners, wax, polish
    CONSUMABLE = "CONSUMABLE"      # sandpaper, tape, cloth
    PART = "PART"                  # bolts, clips, cables
    OTHER = "OTHER"


MATERIAL_CATEGORIES: list[str] = [c.value for c in MaterialCategory]

MATERIAL_CATEGORY_LABELS: dict[str, str] = {
    MaterialCategory.PRIMER.value:     "Primer",
    MaterialCategory.BASECOAT.value:   "Basecoat",
    MaterialCategory.CLEARCOAT.value:  "Clearcoat",
    MaterialCategory.THINNER.value:    "Thinner",
    MaterialCategory.CHEMICAL.value:   "Chemical",
    MaterialCategory.CONSUMABLE.value: "Consumable",
    MaterialCategory.PART.value:       "Part",
    MaterialCategory.OTHER.value:      "Other",
}

MATERIAL_CATEGORY_TONE: dict[str, str] = {
    MaterialCategory.PRIMER.value:     "badge-info",
    MaterialCategory.BASECOAT.value:   "badge-info",
    MaterialCategory.CLEARCOAT.value:  "badge-accent",
    MaterialCategory.THINNER.value:    "badge-neutral",
    MaterialCategory.CHEMICAL.value:   "badge-warning",
    MaterialCategory.CONSUMABLE.value: "badge-neutral",
    MaterialCategory.PART.value:       "badge-accent",
    MaterialCategory.OTHER.value:      "badge-neutral",
}

MATERIAL_SORT_OPTIONS: dict[str, str] = {
    "category_name":  "Category, then name",
    "name_asc":       "Name (A→Z)",
    "name_desc":      "Name (Z→A)",
    "code_asc":       "Code (A→Z)",
    "created_desc":   "Newest first",
}


# ════════════════════════════════════════════════════════════════
# UNITS
# ════════════════════════════════════════════════════════════════

class Unit(StrEnum):
    ML = "ml"
    LITER = "liter"
    GR = "gr"
    KG = "kg"
    PIECE = "piece"
    BOX = "box"
    SET = "set"
    ROLL = "roll"
    METER = "meter"
    CAN = "can"
    BOTTLE = "bottle"


UNITS: list[str] = [u.value for u in Unit]


# ════════════════════════════════════════════════════════════════
# TRANSACTION TYPES
# ════════════════════════════════════════════════════════════════

class TransactionType(StrEnum):
    OPENING = "OPENING"                    # initial stock when system went live
    PURCHASE = "PURCHASE"                  # + received from supplier
    CONSUMPTION = "CONSUMPTION"            # - used on a project
    WASTE = "WASTE"                        # - spilled, dried, contaminated
    ADJUSTMENT_IN = "ADJUSTMENT_IN"        # + correction (found stock)
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"      # - correction (miscount)
    RETURN = "RETURN"                      # - returned to supplier
    TRANSFER_IN = "TRANSFER_IN"            # + from another location
    TRANSFER_OUT = "TRANSFER_OUT"          # - to another location


TRANSACTION_TYPES: list[str] = [t.value for t in TransactionType]

TRANSACTION_TYPE_LABELS: dict[str, str] = {
    TransactionType.OPENING.value:        "Opening stock",
    TransactionType.PURCHASE.value:       "Purchase",
    TransactionType.CONSUMPTION.value:    "Consumption",
    TransactionType.WASTE.value:          "Waste",
    TransactionType.ADJUSTMENT_IN.value:  "Adjustment (in)",
    TransactionType.ADJUSTMENT_OUT.value: "Adjustment (out)",
    TransactionType.RETURN.value:         "Return",
    TransactionType.TRANSFER_IN.value:    "Transfer in",
    TransactionType.TRANSFER_OUT.value:   "Transfer out",
}

TRANSACTION_TYPE_TONE: dict[str, str] = {
    TransactionType.OPENING.value:        "badge-neutral",
    TransactionType.PURCHASE.value:       "badge-success",
    TransactionType.CONSUMPTION.value:    "badge-accent",
    TransactionType.WASTE.value:          "badge-danger",
    TransactionType.ADJUSTMENT_IN.value:  "badge-info",
    TransactionType.ADJUSTMENT_OUT.value: "badge-warning",
    TransactionType.RETURN.value:         "badge-warning",
    TransactionType.TRANSFER_IN.value:    "badge-info",
    TransactionType.TRANSFER_OUT.value:   "badge-neutral",
}

TRANSACTION_SORT_OPTIONS: dict[str, str] = {
    "created_desc": "Newest first",
    "created_asc":  "Oldest first",
}

INBOUND_TYPES: frozenset[str] = frozenset({
    TransactionType.OPENING.value,
    TransactionType.PURCHASE.value,
    TransactionType.ADJUSTMENT_IN.value,
    TransactionType.TRANSFER_IN.value,
})

OUTBOUND_TYPES: frozenset[str] = frozenset({
    TransactionType.CONSUMPTION.value,
    TransactionType.WASTE.value,
    TransactionType.ADJUSTMENT_OUT.value,
    TransactionType.RETURN.value,
    TransactionType.TRANSFER_OUT.value,
})


def signed_quantity(transaction_type: str, quantity: float) -> float:
    """Return quantity with sign based on transaction direction."""
    return float(quantity) if transaction_type in INBOUND_TYPES else -float(quantity)


# ════════════════════════════════════════════════════════════════
# PURCHASE ORDERS
# ════════════════════════════════════════════════════════════════

class PurchaseOrderStatus(StrEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


PURCHASE_ORDER_STATUSES: list[str] = [s.value for s in PurchaseOrderStatus]

PURCHASE_ORDER_STATUS_LABELS: dict[str, str] = {
    PurchaseOrderStatus.DRAFT.value:     "Draft",
    PurchaseOrderStatus.SENT.value:      "Sent to supplier",
    PurchaseOrderStatus.RECEIVED.value:  "Received",
    PurchaseOrderStatus.CLOSED.value:    "Closed",
    PurchaseOrderStatus.CANCELLED.value: "Cancelled",
}

PURCHASE_ORDER_STATUS_TONE: dict[str, str] = {
    PurchaseOrderStatus.DRAFT.value:     "badge-neutral",
    PurchaseOrderStatus.SENT.value:      "badge-info",
    PurchaseOrderStatus.RECEIVED.value:  "badge-success",
    PurchaseOrderStatus.CLOSED.value:    "badge-neutral",
    PurchaseOrderStatus.CANCELLED.value: "badge-danger",
}

TERMINAL_PO_STATUSES: frozenset[str] = frozenset({
    PurchaseOrderStatus.CLOSED.value,
    PurchaseOrderStatus.CANCELLED.value,
})

PO_SORT_OPTIONS: dict[str, str] = {
    "created_desc": "Newest first",
    "created_asc":  "Oldest first",
    "order_desc":   "Order date (newest)",
    "expected_asc": "Expected date (soonest)",
}


# ════════════════════════════════════════════════════════════════
# REFERENCE TYPES
# ════════════════════════════════════════════════════════════════

class ReferenceType(StrEnum):
    PURCHASE_ORDER = "PURCHASE_ORDER"
    PROJECT = "PROJECT"
    MANUAL = "MANUAL"


# ════════════════════════════════════════════════════════════════
# UI HELPERS
# ════════════════════════════════════════════════════════════════

MATERIAL_CATEGORY_TONE: dict[str, str] = {
    MaterialCategory.PRIMER.value:     "badge-info",
    MaterialCategory.BASECOAT.value:   "badge-info",
    MaterialCategory.CLEARCOAT.value:  "badge-accent",
    MaterialCategory.THINNER.value:    "badge-neutral",
    MaterialCategory.CHEMICAL.value:   "badge-warning",
    MaterialCategory.CONSUMABLE.value: "badge-neutral",
    MaterialCategory.PART.value:       "badge-accent",
    MaterialCategory.OTHER.value:      "badge-neutral",
}

MATERIAL_SORT_OPTIONS: dict[str, str] = {
    "category_name": "Category, then name",
    "name_asc":      "Name (A→Z)",
    "name_desc":     "Name (Z→A)",
    "code_asc":      "Code (A→Z)",
    "created_desc":  "Newest first",
}

# Material forms can only use a subset of transaction types
# (PURCHASE and RETURN are reserved for the PO workflow).
MANUAL_TRANSACTION_TYPES: list[str] = [
    TransactionType.CONSUMPTION.value,
    TransactionType.WASTE.value,
    TransactionType.ADJUSTMENT_IN.value,
    TransactionType.ADJUSTMENT_OUT.value,
    TransactionType.OPENING.value,
    TransactionType.TRANSFER_IN.value,
    TransactionType.TRANSFER_OUT.value,
]

