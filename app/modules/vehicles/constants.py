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