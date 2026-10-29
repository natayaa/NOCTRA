"""Schema-level guards for manual stock movements and public intake."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.inventory.schemas import InventoryTransactionCreate
from app.services.public_intake import PublicIntakePayload


def _movement(**overrides):
    base = {
        "material_id": uuid4(),
        "transaction_type": "ADJUSTMENT_IN",
        "quantity": 1,
    }
    return InventoryTransactionCreate(**{**base, **overrides})


def test_manual_movement_needs_no_reference_id():
    # The material page posts reference_type=MANUAL without an id; this used
    # to fail the pair validator and made every UI stock adjustment a 400.
    payload = _movement(reference_type="MANUAL")
    assert payload.reference_type == "MANUAL"
    assert payload.reference_id is None


def test_entity_reference_requires_id():
    with pytest.raises(ValidationError):
        _movement(reference_type="PURCHASE_ORDER")
    with pytest.raises(ValidationError):
        _movement(reference_type="PROJECT")


def test_reference_id_without_type_rejected():
    with pytest.raises(ValidationError):
        _movement(reference_id=uuid4())


def test_reference_pair_accepted():
    rid = uuid4()
    payload = _movement(reference_type="PROJECT", reference_id=rid)
    assert payload.reference_id == rid


def _intake(**overrides):
    base = {
        "name": "Ivan",
        "phone": "081234567890",
        "description": "Full repaint with custom graphics and clear coat.",
    }
    return PublicIntakePayload(**{**base, **overrides})


def test_intake_accepts_minimal_payload():
    payload = _intake()
    assert payload.vehicle_year is None
    assert payload.preferences is None


def test_intake_rejects_oversized_fields():
    with pytest.raises(ValidationError):
        _intake(name="x" * 256)
    with pytest.raises(ValidationError):
        _intake(phone="0" * 33)


def test_intake_rejects_out_of_range_year():
    with pytest.raises(ValidationError):
        _intake(vehicle_year=1200)
    with pytest.raises(ValidationError):
        _intake(vehicle_year=3000)


def test_intake_rejects_oversized_description():
    with pytest.raises(ValidationError):
        _intake(description="x" * 5001)
