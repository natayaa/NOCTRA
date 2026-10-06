"""Material unit-conversion math tests."""

from app.modules.inventory.models import Material


def test_cost_per_stock_unit_from_liter():
    m = Material(
        code="X",
        name="Belkote Clear",
        category="CLEARCOAT",
        purchase_unit="bottle",
        stock_unit="ml",
        stock_units_per_purchase=1000,
        current_purchase_price=450_000,
    )
    assert m.cost_per_stock_unit == 450.0


def test_cost_per_stock_unit_zero_packages():
    m = Material(
        code="Y",
        name="Zero",
        category="OTHER",
        purchase_unit="piece",
        stock_unit="piece",
        stock_units_per_purchase=0,
        current_purchase_price=1000,
    )
    assert m.cost_per_stock_unit == 0.0