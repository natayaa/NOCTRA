"""Inquiry workflow and customer-request vocabulary."""
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from app.core.config import settings


def today_local() -> date:
    """Today's date in the app's configured timezone (not UTC)."""
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


# ════════════════════════════════════════════════════════════════
# PIPELINE
# ════════════════════════════════════════════════════════════════

class InquiryStatus(StrEnum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUOTED = "QUOTED"
    NEGOTIATING = "NEGOTIATING"
    APPROVED = "APPROVED"
    CONVERTED = "CONVERTED"
    LOST = "LOST"


class InquirySource(StrEnum):
    WEBSITE = "WEBSITE"
    WALK_IN = "WALK_IN"
    REFERRAL = "REFERRAL"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    PHONE = "PHONE"
    ADMIN = "ADMIN"


INQUIRY_STATUSES: list[str] = [s.value for s in InquiryStatus]
INQUIRY_SOURCES: list[str] = [s.value for s in InquirySource]

INQUIRY_STATUS_LABELS: dict[str, str] = {
    InquiryStatus.NEW.value: "New",
    InquiryStatus.CONTACTED.value: "Contacted",
    InquiryStatus.QUOTED.value: "Quoted",
    InquiryStatus.NEGOTIATING.value: "Negotiating",
    InquiryStatus.APPROVED.value: "Approved",
    InquiryStatus.CONVERTED.value: "Converted",
    InquiryStatus.LOST.value: "Lost",
}

SOURCE_LABELS: dict[str, str] = {
    "WEBSITE": "Website",
    "WALK_IN": "Walk-in",
    "REFERRAL": "Referral",
    "SOCIAL_MEDIA": "Social Media",
    "PHONE": "Phone",
    "ADMIN": "Admin Entry",
}

STATUS_TONE: dict[str, str] = {
    InquiryStatus.NEW.value: "badge-info",
    InquiryStatus.CONTACTED.value: "badge-neutral",
    InquiryStatus.QUOTED.value: "badge-accent",
    InquiryStatus.NEGOTIATING.value: "badge-warning",
    InquiryStatus.APPROVED.value: "badge-success",
    InquiryStatus.CONVERTED.value: "badge-success",
    InquiryStatus.LOST.value: "badge-danger",
}

# OPEN_STATUSES = pre-approval states (still need active follow-up).
OPEN_STATUSES: frozenset[str] = frozenset({
    InquiryStatus.NEW.value,
    InquiryStatus.CONTACTED.value,
    InquiryStatus.QUOTED.value,
    InquiryStatus.NEGOTIATING.value,
})

TERMINAL_STATUSES: frozenset[str] = frozenset({
    InquiryStatus.CONVERTED.value,
    InquiryStatus.LOST.value,
})

# NON_TERMINAL_STATUSES = everything still actionable (includes APPROVED).
# Used by the `only_open=true` filter so the list and dashboard agree.
NON_TERMINAL_STATUSES: frozenset[str] = frozenset(INQUIRY_STATUSES) - TERMINAL_STATUSES

# Statuses that imply the customer was actually contacted by sales.
# Used to refresh `last_contacted_at` on workflow transitions.
CONTACT_IMPLYING_STATUSES: frozenset[str] = frozenset({
    InquiryStatus.CONTACTED.value,
    InquiryStatus.QUOTED.value,
    InquiryStatus.NEGOTIATING.value,
    InquiryStatus.APPROVED.value,
})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    InquiryStatus.NEW.value: frozenset({
        InquiryStatus.CONTACTED.value,
        InquiryStatus.LOST.value,
    }),
    InquiryStatus.CONTACTED.value: frozenset({
        InquiryStatus.QUOTED.value,
        InquiryStatus.LOST.value,
    }),
    InquiryStatus.QUOTED.value: frozenset({
        InquiryStatus.NEGOTIATING.value,
        InquiryStatus.APPROVED.value,
        InquiryStatus.LOST.value,
    }),
    InquiryStatus.NEGOTIATING.value: frozenset({
        InquiryStatus.APPROVED.value,
        InquiryStatus.LOST.value,
    }),
    InquiryStatus.APPROVED.value: frozenset({
        InquiryStatus.CONVERTED.value,
        InquiryStatus.LOST.value,
    }),
    InquiryStatus.CONVERTED.value: frozenset(),
    InquiryStatus.LOST.value: frozenset(),
}

# Sort keys exposed to the UI — validated in the API layer.
SORT_OPTIONS: dict[str, str] = {
    "created_desc": "Newest first",
    "created_asc": "Oldest first",
    "updated_desc": "Recently updated",
    "follow_up_asc": "Follow-up (soonest)",
    "status_asc": "Status (A→Z)",
}

# Upper bound on photos per inquiry — enforced in the service.
MAX_PHOTOS_PER_INQUIRY: int = 20


# ════════════════════════════════════════════════════════════════
# FINISH
# ════════════════════════════════════════════════════════════════

class FinishType(StrEnum):
    GLOSS = "GLOSS"
    WET_GLOSS = "WET_GLOSS"
    SATIN = "SATIN"
    DOFF = "DOFF"
    MATTE = "MATTE"
    METALLIC = "METALLIC"
    PEARL = "PEARL"
    CANDY = "CANDY"
    CUSTOM = "CUSTOM"


FINISH_TYPES: list[str] = [f.value for f in FinishType]

FINISH_LABELS: dict[str, str] = {
    FinishType.GLOSS.value: "Gloss",
    FinishType.WET_GLOSS.value: "Wet gloss",
    FinishType.SATIN.value: "Satin",
    FinishType.DOFF.value: "Doff (eggshell)",
    FinishType.MATTE.value: "Matte",
    FinishType.METALLIC.value: "Metallic",
    FinishType.PEARL.value: "Pearl",
    FinishType.CANDY.value: "Candy",
    FinishType.CUSTOM.value: "Custom / Not sure",
}


# ════════════════════════════════════════════════════════════════
# COLOR
# ════════════════════════════════════════════════════════════════

class ColorFamily(StrEnum):
    BLACK = "BLACK"
    WHITE = "WHITE"
    SILVER = "SILVER"
    GREY = "GREY"
    RED = "RED"
    BLUE = "BLUE"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    ORANGE = "ORANGE"
    BROWN = "BROWN"
    GOLD = "GOLD"
    METALLIC = "METALLIC"
    PEARL = "PEARL"
    CANDY = "CANDY"
    CUSTOM = "CUSTOM"


COLOR_FAMILIES: list[str] = [c.value for c in ColorFamily]

COLOR_LABELS: dict[str, str] = {
    ColorFamily.BLACK.value: "Black",
    ColorFamily.WHITE.value: "White",
    ColorFamily.SILVER.value: "Silver",
    ColorFamily.GREY.value: "Grey",
    ColorFamily.RED.value: "Red",
    ColorFamily.BLUE.value: "Blue",
    ColorFamily.GREEN.value: "Green",
    ColorFamily.YELLOW.value: "Yellow",
    ColorFamily.ORANGE.value: "Orange",
    ColorFamily.BROWN.value: "Brown",
    ColorFamily.GOLD.value: "Gold",
    ColorFamily.METALLIC.value: "Metallic",
    ColorFamily.PEARL.value: "Pearl",
    ColorFamily.CANDY.value: "Candy",
    ColorFamily.CUSTOM.value: "Custom",
}

# Approximate swatch colors for UI. Display-only; not authoritative.
COLOR_SWATCH: dict[str, str] = {
    "BLACK": "#0a0a0a", "WHITE": "#f5f5f5", "SILVER": "#c0c4c9",
    "GREY": "#6b7280", "RED": "#dc2626", "BLUE": "#2563eb",
    "GREEN": "#16a34a", "YELLOW": "#eab308", "ORANGE": "#ea580c",
    "BROWN": "#78350f", "GOLD": "#ca8a04", "METALLIC": "#94a3b8",
    "PEARL": "#e2e8f0", "CANDY": "#ec4899", "CUSTOM": "#64748b",
}


# ════════════════════════════════════════════════════════════════
# BUDGET
# ════════════════════════════════════════════════════════════════

class BudgetRange(StrEnum):
    UNDER_1M = "UNDER_1M"
    R1_3M = "R1_3M"
    R3_5M = "R3_5M"
    R5_10M = "R5_10M"
    OVER_10M = "OVER_10M"
    UNKNOWN = "UNKNOWN"


BUDGET_RANGES: list[str] = [b.value for b in BudgetRange]

BUDGET_LABELS: dict[str, str] = {
    BudgetRange.UNDER_1M.value: "< Rp 1 juta",
    BudgetRange.R1_3M.value: "Rp 1–3 juta",
    BudgetRange.R3_5M.value: "Rp 3–5 juta",
    BudgetRange.R5_10M.value: "Rp 5–10 juta",
    BudgetRange.OVER_10M.value: "> Rp 10 juta",
    BudgetRange.UNKNOWN.value: "Belum tahu",
}


# ════════════════════════════════════════════════════════════════
# SERVICE INTEREST
# ════════════════════════════════════════════════════════════════

class ServiceInterest(StrEnum):
    REPAINT = "REPAINT"
    PANEL_REPAINT = "PANEL_REPAINT"
    RESTORATION = "RESTORATION"
    CUSTOM_PAINT = "CUSTOM_PAINT"
    DETAILING = "DETAILING"
    PANEL_REPAIR = "PANEL_REPAIR"
    OTHER = "OTHER"


SERVICE_INTERESTS: list[str] = [s.value for s in ServiceInterest]

SERVICE_INTEREST_LABELS: dict[str, str] = {
    ServiceInterest.REPAINT.value: "Full body repaint",
    ServiceInterest.PANEL_REPAINT.value: "Panel repaint",
    ServiceInterest.RESTORATION.value: "Restoration",
    ServiceInterest.CUSTOM_PAINT.value: "Custom paint",
    ServiceInterest.DETAILING.value: "Detailing & polish",
    ServiceInterest.PANEL_REPAIR.value: "Panel repair",
    ServiceInterest.OTHER.value: "Other / not sure",
}


# ════════════════════════════════════════════════════════════════
# FLEXIBLE PREFERENCES (JSONB)
# ════════════════════════════════════════════════════════════════

PREFERENCE_KEYS: list[dict] = [
    {"key": "keep_decals", "label": "Preserve original decals", "type": "bool"},
    {"key": "pinstripe", "label": "Pinstriping", "type": "text"},
    {"key": "chrome_work", "label": "Chrome polish areas", "type": "list"},
    {"key": "preferred_brand_clearcoat", "label": "Preferred clearcoat brand", "type": "string"},
    {"key": "matching_oem_color", "label": "Match OEM color", "type": "string"},
    {"key": "reference_photo_url", "label": "Reference photo URL", "type": "string"},
    {"key": "custom_notes", "label": "Other special requests", "type": "text"},
]

PREFERENCE_LIST_KEYS: frozenset[str] = frozenset(
    p["key"] for p in PREFERENCE_KEYS if p["type"] == "list"
)