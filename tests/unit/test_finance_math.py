"""Pricing and costing math tests."""

import pytest

from app.modules.pricing.service import (
    margin_of,
    markup_of,
    price_from_margin,
    price_from_markup,
)


def test_price_from_margin_50pct():
    assert price_from_margin(400_000, 50) == 800_000


def test_price_from_margin_roundtrip():
    hpp = 400_000
    price = price_from_margin(hpp, 55)
    assert abs(margin_of(price, hpp) - 55) < 0.01


def test_margin_vs_markup_differ():
    hpp = 400_000
    price = 800_000
    assert margin_of(price, hpp) == 50.0
    assert markup_of(price, hpp) == 100.0


def test_price_from_markup_100pct():
    assert price_from_markup(400_000, 100) == 800_000


def test_margin_of_zero_price():
    assert margin_of(0, 400_000) == 0.0


def test_markup_of_zero_hpp():
    assert markup_of(800_000, 0) == 0.0


def test_price_from_margin_100pct_invalid():
    with pytest.raises(ValueError):
        price_from_margin(400_000, 100)