"""Margin health classification tests."""

from app.modules.pricing.constants import margin_health_label


def test_loss():
    assert margin_health_label(
        actual_margin_pct=-5, target_margin_pct=50, min_margin_pct=30
    ) == "loss"


def test_below_minimum():
    assert margin_health_label(
        actual_margin_pct=20, target_margin_pct=50, min_margin_pct=30
    ) == "below_minimum"


def test_acceptable():
    assert margin_health_label(
        actual_margin_pct=40, target_margin_pct=50, min_margin_pct=30
    ) == "acceptable"


def test_good_at_target():
    assert margin_health_label(
        actual_margin_pct=50, target_margin_pct=50, min_margin_pct=30
    ) == "good"


def test_excellent_well_above_target():
    assert margin_health_label(
        actual_margin_pct=60, target_margin_pct=50, min_margin_pct=30
    ) == "excellent"