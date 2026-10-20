"""Project workflow and costing vocabulary."""

from __future__ import annotations

from enum import StrEnum


# ════════════════════════════════════════════════════════════════
# PROJECT LIFECYCLE
# ════════════════════════════════════════════════════════════════

class ProjectStatus(StrEnum):
    DRAFT = "DRAFT"
    ESTIMATING = "ESTIMATING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    PAINTING = "PAINTING"
    ASSEMBLY = "ASSEMBLY"
    QC = "QC"
    COMPLETED = "COMPLETED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


PROJECT_STATUSES: list[str] = [s.value for s in ProjectStatus]

PROJECT_STATUS_LABELS: dict[str, str] = {
    ProjectStatus.DRAFT.value:            "Draft",
    ProjectStatus.ESTIMATING.value:       "Estimating",
    ProjectStatus.WAITING_APPROVAL.value: "Waiting approval",
    ProjectStatus.APPROVED.value:         "Approved",
    ProjectStatus.IN_PROGRESS.value:      "In progress",
    ProjectStatus.PAINTING.value:         "Painting",
    ProjectStatus.ASSEMBLY.value:         "Assembly",
    ProjectStatus.QC.value:               "Quality check",
    ProjectStatus.COMPLETED.value:        "Completed",
    ProjectStatus.DELIVERED.value:        "Delivered",
    ProjectStatus.CANCELLED.value:        "Cancelled",
}

PROJECT_STATUS_TONE: dict[str, str] = {
    ProjectStatus.DRAFT.value:            "badge-neutral",
    ProjectStatus.ESTIMATING.value:       "badge-info",
    ProjectStatus.WAITING_APPROVAL.value: "badge-warning",
    ProjectStatus.APPROVED.value:         "badge-accent",
    ProjectStatus.IN_PROGRESS.value:      "badge-accent",
    ProjectStatus.PAINTING.value:         "badge-accent",
    ProjectStatus.ASSEMBLY.value:         "badge-accent",
    ProjectStatus.QC.value:               "badge-warning",
    ProjectStatus.COMPLETED.value:        "badge-success",
    ProjectStatus.DELIVERED.value:        "badge-success",
    ProjectStatus.CANCELLED.value:        "badge-danger",
}

TERMINAL_PROJECT_STATUSES: frozenset[str] = frozenset({
    ProjectStatus.DELIVERED.value,
    ProjectStatus.CANCELLED.value,
})

ALLOWED_PROJECT_TRANSITIONS: dict[str, frozenset[str]] = {
    ProjectStatus.DRAFT.value: frozenset({
        ProjectStatus.ESTIMATING.value,
        ProjectStatus.CANCELLED.value,
    }),
    ProjectStatus.ESTIMATING.value: frozenset({
        ProjectStatus.WAITING_APPROVAL.value,
        ProjectStatus.DRAFT.value,
        ProjectStatus.CANCELLED.value,
    }),
    ProjectStatus.WAITING_APPROVAL.value: frozenset({
        ProjectStatus.APPROVED.value,
        ProjectStatus.ESTIMATING.value,
        ProjectStatus.CANCELLED.value,
    }),
    ProjectStatus.APPROVED.value: frozenset({
        ProjectStatus.IN_PROGRESS.value,
        ProjectStatus.CANCELLED.value,
    }),
    ProjectStatus.IN_PROGRESS.value: frozenset({
        ProjectStatus.PAINTING.value,
        ProjectStatus.QC.value,
        ProjectStatus.CANCELLED.value,
    }),
    ProjectStatus.PAINTING.value: frozenset({
        ProjectStatus.ASSEMBLY.value,
        ProjectStatus.CANCELLED.value,
    }),
    ProjectStatus.ASSEMBLY.value: frozenset({
        ProjectStatus.QC.value,
        ProjectStatus.CANCELLED.value,
    }),
    ProjectStatus.QC.value: frozenset({
        ProjectStatus.COMPLETED.value,
        ProjectStatus.IN_PROGRESS.value,
    }),
    ProjectStatus.COMPLETED.value: frozenset({
        ProjectStatus.DELIVERED.value,
    }),
    ProjectStatus.DELIVERED.value: frozenset(),
    ProjectStatus.CANCELLED.value: frozenset(),
}


# ════════════════════════════════════════════════════════════════
# SORTING
# ════════════════════════════════════════════════════════════════

PROJECT_SORT_OPTIONS: dict[str, str] = {
    "created_desc":  "Newest first",
    "created_asc":   "Oldest first",
    "updated_desc":  "Recently updated",
    "target_asc":    "Target date (soonest)",
    "priority_desc": "Priority (high→low)",
}


# ════════════════════════════════════════════════════════════════
# COST CATEGORIES
# ════════════════════════════════════════════════════════════════

class CostCategory(StrEnum):
    MATERIAL = "MATERIAL"
    PART = "PART"
    LABOR = "LABOR"
    OUTSOURCE = "OUTSOURCE"
    OVERHEAD = "OVERHEAD"
    MISC = "MISC"


COST_CATEGORIES: list[str] = [c.value for c in CostCategory]

COST_CATEGORY_LABELS: dict[str, str] = {
    CostCategory.MATERIAL.value:  "Materials",
    CostCategory.PART.value:      "Parts",
    CostCategory.LABOR.value:     "Labor",
    CostCategory.OUTSOURCE.value: "Outsourcing",
    CostCategory.OVERHEAD.value:  "Overhead",
    CostCategory.MISC.value:      "Miscellaneous",
}

INVENTORY_CATEGORIES: frozenset[str] = frozenset({
    CostCategory.MATERIAL.value,
    CostCategory.PART.value,
})

LABOR_CATEGORIES: frozenset[str] = frozenset({
    CostCategory.LABOR.value,
})


# ════════════════════════════════════════════════════════════════
# PROJECT ITEM STATE
# ════════════════════════════════════════════════════════════════

class ProjectItemStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


PROJECT_ITEM_STATUSES: list[str] = [s.value for s in ProjectItemStatus]

PROJECT_ITEM_STATUS_LABELS: dict[str, str] = {
    ProjectItemStatus.PLANNED.value:     "Planned",
    ProjectItemStatus.IN_PROGRESS.value: "In progress",
    ProjectItemStatus.COMPLETED.value:   "Completed",
}

PROJECT_ITEM_STATUS_TONE: dict[str, str] = {
    ProjectItemStatus.PLANNED.value:     "badge-neutral",
    ProjectItemStatus.IN_PROGRESS.value: "badge-accent",
    ProjectItemStatus.COMPLETED.value:   "badge-success",
}


# ════════════════════════════════════════════════════════════════
# SETTINGS KEYS
#
# NOTE: SETTING_DEFAULT_MARGIN_PCT / SETTING_MINIMUM_MARGIN_PCT are
# the same keys used by the pricing module (imported there under the
# names SETTING_DEFAULT_TARGET_MARGIN / SETTING_MIN_MARGIN). Keep
# both modules' constant names but never change the string values.
# ════════════════════════════════════════════════════════════════

SETTING_MONTHLY_OVERHEAD = "costing.overhead_monthly"
SETTING_MONTHLY_LABOR_HOURS = "costing.monthly_labor_hours"
SETTING_DEFAULT_MARGIN_PCT = "costing.default_target_margin_pct"
SETTING_MINIMUM_MARGIN_PCT = "costing.minimum_margin_pct"