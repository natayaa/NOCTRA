"""Inquiry workflow and customer-request vocabulary.

The inquiry captures two things:
  1. Where the customer is in the sales pipeline (`InquiryStatus`).
  2. What the customer actually wants (`FinishType`, `ColorFamily`,
     and the flexible `preferences` JSONB blob).

Fixed enums are for values we filter, price, or report on.
The `preferences` JSONB column holds everything else.
"""

from __future__ import annotations

from enum import StrEnum


# ════════════════════════════════════════════════════════════════
# PIPELINE
# ════════════════════════════════════════════════════════════════

class InquiryStatus(StrEnum):
    NEW = "NEW"                    # just submitted, unread
    CONTACTED = "CONTACTED"        # sales has reached out
    QUOTED = "QUOTED"              # quote sent
    NEGOTIATING = "NEGOTIATING"    # customer wants changes
    APPROVED = "APPROVED"          # ready to become a project
    CONVERTED = "CONVERTED"        # became a project (terminal)
    LOST = "LOST"                  # declined or went silent (terminal)


class InquirySource(StrEnum):
    WEBSITE = "WEBSITE"
    WALK_IN = "WALK_IN"
    REFERRAL = "REFERRAL"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    PHONE = "PHONE"
    ADMIN = "ADMIN"


INQUIRY_STATUSES: list[str] = [s.value for s in InquiryStatus]
INQUIRY_SOURCES: list[str] = [s.value for s in InquirySource]

TERMINAL_STATUSES: frozenset[str] = frozenset({
    InquiryStatus.CONVERTED.value,
    InquiryStatus.LOST.value,
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


# ════════════════════════════════════════════════════════════════
# CUSTOMER REQUEST — FINISH
# ════════════════════════════════════════════════════════════════

class FinishType(StrEnum):
    GLOSS = "GLOSS"           # standard high-gloss clear
    WET_GLOSS = "WET_GLOSS"   # deep "wet look"
    SATIN = "SATIN"           # ~35-45% gloss, semi-gloss
    DOFF = "DOFF"             # ~15-25% gloss, eggshell/semi-matte
    MATTE = "MATTE"           # ~5-10% gloss, flat
    METALLIC = "METALLIC"     # metallic-flake clear
    PEARL = "PEARL"           # pearlescent
    CANDY = "CANDY"           # tinted/candy clear
    CUSTOM = "CUSTOM"         # anything else


FINISH_TYPES: list[str] = [f.value for f in FinishType]

FINISH_LABELS: dict[str, str] = {
    FinishType.GLOSS.value:     "Gloss",
    FinishType.WET_GLOSS.value: "Wet gloss",
    FinishType.SATIN.value:     "Satin",
    FinishType.DOFF.value:      "Doff (eggshell)",
    FinishType.MATTE.value:     "Matte",
    FinishType.METALLIC.value:  "Metallic",
    FinishType.PEARL.value:     "Pearl",
    FinishType.CANDY.value:     "Candy",
    FinishType.CUSTOM.value:    "Custom / Not sure",
}


# ════════════════════════════════════════════════════════════════
# CUSTOMER REQUEST — COLOR
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
    ColorFamily.BLACK.value:    "Black",
    ColorFamily.WHITE.value:    "White",
    ColorFamily.SILVER.value:   "Silver",
    ColorFamily.GREY.value:     "Grey",
    ColorFamily.RED.value:      "Red",
    ColorFamily.BLUE.value:     "Blue",
    ColorFamily.GREEN.value:    "Green",
    ColorFamily.YELLOW.value:   "Yellow",
    ColorFamily.ORANGE.value:   "Orange",
    ColorFamily.BROWN.value:    "Brown",
    ColorFamily.GOLD.value:     "Gold",
    ColorFamily.METALLIC.value: "Metallic",
    ColorFamily.PEARL.value:    "Pearl",
    ColorFamily.CANDY.value:    "Candy",
    ColorFamily.CUSTOM.value:   "Custom",
}


# ════════════════════════════════════════════════════════════════
# BUDGET BUCKETS
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
    BudgetRange.UNDER_1M.value:  "< Rp 1 juta",
    BudgetRange.R1_3M.value:     "Rp 1–3 juta",
    BudgetRange.R3_5M.value:     "Rp 3–5 juta",
    BudgetRange.R5_10M.value:    "Rp 5–10 juta",
    BudgetRange.OVER_10M.value:  "> Rp 10 juta",
    BudgetRange.UNKNOWN.value:   "Belum tahu",
}


# ════════════════════════════════════════════════════════════════
# SERVICE INTEREST — free-form string but suggested values
# ════════════════════════════════════════════════════════════════

SERVICE_INTERESTS: list[str] = [
    "REPAINT",
    "PANEL_REPAINT",
    "RESTORATION",
    "CUSTOM_PAINT",
    "DETAILING",
    "PANEL_REPAIR",
    "OTHER",
]

SERVICE_INTEREST_LABELS: dict[str, str] = {
    "REPAINT":       "Full body repaint",
    "PANEL_REPAINT": "Panel repaint",
    "RESTORATION":   "Restoration",
    "CUSTOM_PAINT":  "Custom paint",
    "DETAILING":     "Detailing & polish",
    "PANEL_REPAIR":  "Panel repair",
    "OTHER":         "Other / not sure",
}


# ════════════════════════════════════════════════════════════════
# FLEXIBLE PREFERENCES (JSONB)
#
# A list of "known" preference keys. The UI iterates over this to
# render dynamic inputs. Extra keys in the JSONB are allowed — this
# is a hint, not a constraint.
# ════════════════════════════════════════════════════════════════

PREFERENCE_KEYS: list[dict] = [
    {
        "key": "keep_decals",
        "label": "Preserve original decals",
        "type": "bool",
    },
    {
        "key": "pinstripe",
        "label": "Pinstriping",
        "type": "json",              # {"color": "...", "location": "..."}
    },
    {
        "key": "chrome_work",
        "label": "Chrome polish areas",
        "type": "list",              # ["engine_cover", "exhaust_tip"]
    },
    {
        "key": "preferred_brand_clearcoat",
        "label": "Preferred clearcoat brand",
        "type": "string",
    },
    {
        "key": "matching_oem_color",
        "label": "Match OEM color",
        "type": "string",
    },
    {
        "key": "reference_photo_url",
        "label": "Reference photo URL",
        "type": "string",
    },
    {
        "key": "custom_notes",
        "label": "Other special requests",
        "type": "text",
    },
]