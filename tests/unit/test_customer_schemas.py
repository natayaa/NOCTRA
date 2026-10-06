"""Customer schema validation — Phase 2a."""

import pytest
from pydantic import ValidationError

from app.modules.customers.schemas import (
    CustomerContactIn,
    CustomerCreate,
    CustomerUpdate,
)


def test_create_minimal():
    c = CustomerCreate(name="Ivan", phone="081234567890")
    assert c.name == "Ivan"
    assert c.phone == "081234567890"
    assert c.country == "Indonesia"


def test_name_too_short_rejected():
    with pytest.raises(ValidationError):
        CustomerCreate(name="I", phone="081234567890")


def test_invalid_phone_rejected():
    with pytest.raises(ValidationError):
        CustomerCreate(name="Ivan", phone="abc")


def test_phone_allows_international_format():
    c = CustomerCreate(name="Ivan", phone="+62 812-3456-7890")
    assert c.phone == "+62 812-3456-7890"


def test_blank_email_becomes_none():
    c = CustomerCreate(name="Ivan", phone="081234567890", email="")
    assert c.email is None


def test_valid_email_kept():
    c = CustomerCreate(name="Ivan", phone="081234567890", email="ivan@noctra.local")
    assert str(c.email) == "ivan@noctra.local"


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        CustomerCreate(name="Ivan", phone="081234567890", email="not-an-email")


def test_update_allows_all_none():
    u = CustomerUpdate()
    assert u.name is None
    assert u.email is None
    assert u.phone is None


def test_update_partial():
    u = CustomerUpdate(city="Jakarta")
    assert u.city == "Jakarta"
    assert u.name is None


def test_contact_requires_name():
    with pytest.raises(ValidationError):
        CustomerContactIn(name="A")


def test_contact_role_optional():
    c = CustomerContactIn(name="Siti")
    assert c.role is None