from __future__ import annotations

from enum import StrEnum


class CustomerStatus(StrEnum):
    LEAD = "LEAD"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    BLOCKED = "BLOCKED"


class CustomerSource(StrEnum):
    WEBSITE = "WEBSITE"
    WALK_IN = "WALK_IN"
    REFERRAL = "REFERRAL"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    PHONE = "PHONE"
    ADMIN = "ADMIN"


CUSTOMER_STATUSES: list[str] = [s.value for s in CustomerStatus]
CUSTOMER_SOURCES: list[str] = [s.value for s in CustomerSource]

CUSTOMER_STATUS_LABELS: dict[str, str] = {
    CustomerStatus.LEAD.value:     "Lead",
    CustomerStatus.ACTIVE.value:   "Active",
    CustomerStatus.INACTIVE.value: "Inactive",
    CustomerStatus.BLOCKED.value:  "Blocked",
}

CUSTOMER_SOURCE_LABELS: dict[str, str] = {
    CustomerSource.WEBSITE.value:      "Website",
    CustomerSource.WALK_IN.value:      "Walk-in",
    CustomerSource.REFERRAL.value:     "Referral",
    CustomerSource.SOCIAL_MEDIA.value: "Social media",
    CustomerSource.PHONE.value:        "Phone",
    CustomerSource.ADMIN.value:        "Admin",
}

# Single source of truth for status → badge tone in templates
STATUS_TONE: dict[str, str] = {
    CustomerStatus.LEAD.value:     "badge-info",
    CustomerStatus.ACTIVE.value:   "badge-success",
    CustomerStatus.INACTIVE.value: "badge-neutral",
    CustomerStatus.BLOCKED.value:  "badge-danger",
}

# Active/pending statuses (used for filtering on list page)
ACTIVE_STATUSES: frozenset[str] = frozenset({
    CustomerStatus.LEAD.value,
    CustomerStatus.ACTIVE.value,
})

# Sort keys exposed to the UI
CUSTOMER_SORT_OPTIONS: dict[str, str] = {
    "created_desc": "Newest first",
    "created_asc":  "Oldest first",
    "name_asc":     "Name (A→Z)",
    "name_desc":    "Name (Z→A)",
    "updated_desc": "Recently updated",
}