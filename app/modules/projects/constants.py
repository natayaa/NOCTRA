"""Project workflow and costing vocabulary."""

from __future__ import annotations

from enum import StrEnum


# ════════════════════════════════════════════════════════════════
# PROJECT LIFECYCLE
# ════════════════════════════════════════════════════════════════

class ProjectStatus(StrEnum):
    DRAFT = "DRAFT"                    # created, not yet quoted
    ESTIMATING = "ESTIMATING"          # costs being worked out
    WAITING_APPROVAL = "WAITING_APPROVAL"  # quoted, waiting for customer
    APPROVED = "APPROVED"              # customer accepted
    IN_PROGRESS = "IN_PROGRESS"        # work started
    PAINTING = "PAINTING"              # in paint booth
    ASSEMBLY = "ASSEMBLY"              # reassembling after paint
    QC = "QC"                          # quality check
    COMPLETED = "COMPLETED"            # work done, awaiting pickup
    DELIVERED = "DELIVERED"            # picked up
    CANCELLED = "CANCELLED"            # terminated


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

# Which statuses are "terminal" (no further work expected)
TERMINAL_PROJECT_STATUSES: frozenset[str] = frozenset({
    ProjectStatus.DELIVERED.value,
    ProjectStatus.CANCELLED.value,
})

# Allowed status transitions
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
# COST CATEGORIES
# ════════════════════════════════════════════════════════════════

class CostCategory(StrEnum):
    MATERIAL = "MATERIAL"      # paint, thinner, chemicals (from inventory)
    PART = "PART"              # bolts, clips, replacement parts (from inventory)
    LABOR = "LABOR"            # employee time
    OUTSOURCE = "OUTSOURCE"    # external services (chrome, upholstery, machining)
    OVERHEAD = "OVERHEAD"      # allocated from monthly overhead
    MISC = "MISC"              # miscellaneous / one-off


COST_CATEGORIES: list[str] = [c.value for c in CostCategory]

COST_CATEGORY_LABELS: dict[str, str] = {
    CostCategory.MATERIAL.value:  "Materials",
    CostCategory.PART.value:      "Parts",
    CostCategory.LABOR.value:     "Labor",
    CostCategory.OUTSOURCE.value: "Outsourcing",
    CostCategory.OVERHEAD.value:  "Overhead",
    CostCategory.MISC.value:      "Miscellaneous",
}

# Categories that require a material_id (from inventory)
INVENTORY_CATEGORIES: frozenset[str] = frozenset({
    CostCategory.MATERIAL.value,
    CostCategory.PART.value,
})

# Categories that require an employee_id
LABOR_CATEGORIES: frozenset[str] = frozenset({
    CostCategory.LABOR.value,
})


# ════════════════════════════════════════════════════════════════
# ITEM STATE (for tracking progress at line level)
# ════════════════════════════════════════════════════════════════

class ProjectItemStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


PROJECT_ITEM_STATUSES: list[str] = [s.value for s in ProjectItemStatus]


# ════════════════════════════════════════════════════════════════
# SETTINGS KEYS (already seeded in Phase 1)
# ════════════════════════════════════════════════════════════════

SETTING_MONTHLY_OVERHEAD = "costing.overhead_monthly"
SETTING_MONTHLY_LABOR_HOURS = "costing.monthly_labor_hours"
SETTING_DEFAULT_MARGIN_PCT = "costing.default_target_margin_pct"
SETTING_MINIMUM_MARGIN_PCT = "costing.minimum_margin_pct"