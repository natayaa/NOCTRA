"""Pricing engine constants."""

from __future__ import annotations

DEFAULT_TARGET_MARGIN_PCT: float = 50.0
DEFAULT_MIN_MARGIN_PCT: float = 30.0
DEFAULT_COMPLEXITY_FACTOR: float = 1.0

SETTING_DEFAULT_TARGET_MARGIN = "costing.default_target_margin_pct"
SETTING_MIN_MARGIN = "costing.minimum_margin_pct"


def rule_specificity(
    service_interest: str | None,
    vehicle_category: str | None,
) -> int:
    """
    Compute the match specificity of a pricing rule.

      3 — service + category both specified
      2 — service only
      1 — category only
      0 — global default (both NULL)
    """
    s = 0
    if service_interest:
        s += 2
    if vehicle_category:
        s += 1
    return s


def margin_health_label(
    *,
    actual_margin_pct: float,
    target_margin_pct: float,
    min_margin_pct: float,
) -> str:
    """
    Classify a margin for UI display.

    Returns one of:
      - "loss"           — negative margin
      - "below_minimum"  — positive but under the rule's floor
      - "acceptable"     — between min and target
      - "good"           — at or above target
      - "excellent"      — 5 points above target
    """
    if actual_margin_pct < 0:
        return "loss"
    if actual_margin_pct < min_margin_pct:
        return "below_minimum"
    if actual_margin_pct >= target_margin_pct + 5:
        return "excellent"
    if actual_margin_pct >= target_margin_pct:
        return "good"
    return "acceptable"