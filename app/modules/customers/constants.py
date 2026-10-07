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


CUSTOMER_STATUSES = [s.value for s in CustomerStatus]
CUSTOMER_SOURCES = [s.value for s in CustomerSource]

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