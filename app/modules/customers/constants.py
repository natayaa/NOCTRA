from __future__ import annotations

from enum import StrEnum


class CustomerStatus(StrEnum):
    LEAD = "LEAD"           # from inquiry, not yet qualified
    ACTIVE = "ACTIVE"       # has projects / ongoing
    INACTIVE = "INACTIVE"   # dormant >6 months
    BLOCKED = "BLOCKED"     # do not service


class CustomerSource(StrEnum):
    WEBSITE = "WEBSITE"
    WALK_IN = "WALK_IN"
    REFERRAL = "REFERRAL"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    PHONE = "PHONE"
    ADMIN = "ADMIN"         # created by staff


CUSTOMER_STATUSES = [s.value for s in CustomerStatus]
CUSTOMER_SOURCES = [s.value for s in CustomerSource]