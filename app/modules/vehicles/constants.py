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


VEHICLE_CATEGORIES = [c.value for c in VehicleCategory]

VEHICLE_CATEGORY_LABELS: dict[str, str] = {
    VehicleCategory.SCOOTER.value:   "Scooter",
    VehicleCategory.UNDERBONE.value: "Underbone",
    VehicleCategory.SPORT.value:     "Sport",
    VehicleCategory.NAKED.value:     "Naked",
    VehicleCategory.BIG_BIKE.value:  "Big bike",
    VehicleCategory.CLASSIC.value:   "Classic",
    VehicleCategory.CUSTOM.value:    "Custom",
}