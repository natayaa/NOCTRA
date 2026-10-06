"""Vehicle schema validation — Phase 2a."""

import pytest
from pydantic import ValidationError

from app.modules.vehicles.constants import VEHICLE_CATEGORIES
from app.modules.vehicles.schemas import VehicleCreate, VehicleUpdate


def test_create_minimal():
    v = VehicleCreate(brand="Yamaha", model="Mio")
    assert v.brand == "Yamaha"
    assert v.model == "Mio"


def test_brand_required():
    with pytest.raises(ValidationError):
        VehicleCreate(brand="", model="Mio")


def test_model_required():
    with pytest.raises(ValidationError):
        VehicleCreate(brand="Yamaha", model="")


def test_valid_category_accepted():
    for cat in VEHICLE_CATEGORIES:
        v = VehicleCreate(brand="X", model="Y", category=cat)
        assert v.category == cat


def test_invalid_category_rejected():
    with pytest.raises(ValidationError):
        VehicleCreate(brand="X", model="Y", category="FLYING_CARPET")


def test_year_bounds():
    with pytest.raises(ValidationError):
        VehicleCreate(brand="X", model="Y", year=1800)
    with pytest.raises(ValidationError):
        VehicleCreate(brand="X", model="Y", year=3000)


def test_year_valid_range():
    v = VehicleCreate(brand="X", model="Y", year=2018)
    assert v.year == 2018


def test_update_allows_blank():
    u = VehicleUpdate()
    assert u.brand is None
    assert u.category is None


def test_update_rejects_bad_category():
    with pytest.raises(ValidationError):
        VehicleUpdate(category="ALIEN")