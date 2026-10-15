from __future__ import annotations

from enum import StrEnum


class VehicleCategory(StrEnum):
    SCOOTER = "SCOOTER"
    UNDERBONE = "UNDERBONE"
    SPORT = "SPORT"
    NAKED = "NAKED"
    BIG_BIKE = "BIG_BIKE"
    CLASSIC = "CLASSIC"
    CUSTOM = "CUSTOM"


VEHICLE_CATEGORIES: list[str] = [c.value for c in VehicleCategory]

VEHICLE_CATEGORY_LABELS: dict[str, str] = {
    VehicleCategory.SCOOTER.value:   "Scooter",
    VehicleCategory.UNDERBONE.value: "Underbone",
    VehicleCategory.SPORT.value:     "Sport",
    VehicleCategory.NAKED.value:     "Naked",
    VehicleCategory.BIG_BIKE.value:  "Big bike",
    VehicleCategory.CLASSIC.value:   "Classic",
    VehicleCategory.CUSTOM.value:    "Custom",
}

# Badge tone per category — single source of truth
CATEGORY_TONE: dict[str, str] = {
    VehicleCategory.SCOOTER.value:   "badge-info",
    VehicleCategory.UNDERBONE.value: "badge-info",
    VehicleCategory.SPORT.value:     "badge-accent",
    VehicleCategory.NAKED.value:     "badge-accent",
    VehicleCategory.BIG_BIKE.value:  "badge-warning",
    VehicleCategory.CLASSIC.value:   "badge-success",
    VehicleCategory.CUSTOM.value:    "badge-danger",
}

VEHICLE_SORT_OPTIONS: dict[str, str] = {
    "created_desc": "Newest first",
    "created_asc":  "Oldest first",
    "brand_asc":    "Brand (A→Z)",
    "year_desc":    "Year (newest)",
    "plate_asc":    "Plate (A→Z)",
}