"""Project derived-property tests — Phase 4."""

from uuid import uuid4

from app.modules.projects.constants import (
    ALLOWED_PROJECT_TRANSITIONS,
    COST_CATEGORIES,
    PROJECT_STATUSES,
    TERMINAL_PROJECT_STATUSES,
    CostCategory,
    ProjectStatus,
)
from app.modules.projects.models import Project


def _project(**kw) -> Project:
    defaults = dict(
        code="P-1",
        customer_id=uuid4(),
        estimated_hpp=1_000_000,
        actual_hpp=1_200_000,
        approved_price=2_000_000,
    )
    defaults.update(kw)
    return Project(**defaults)


def test_hpp_variance_positive_when_under():
    p = _project(estimated_hpp=2_000_000, actual_hpp=1_500_000)
    assert p.hpp_variance == 500_000


def test_hpp_variance_negative_when_over():
    p = _project(estimated_hpp=1_000_000, actual_hpp=1_400_000)
    assert p.hpp_variance == -400_000


def test_actual_gross_profit():
    p = _project(approved_price=2_000_000, actual_hpp=1_200_000)
    assert p.actual_gross_profit == 800_000


def test_actual_gross_profit_zero_without_price():
    p = _project(approved_price=None)
    assert p.actual_gross_profit == 0.0


def test_actual_gross_margin_pct():
    p = _project(approved_price=2_000_000, actual_hpp=1_200_000)
    assert p.actual_gross_margin_pct == 40.0


def test_margin_pct_zero_without_price():
    p = _project(approved_price=None)
    assert p.actual_gross_margin_pct == 0.0


def test_estimated_gross_profit():
    p = _project(approved_price=2_000_000, estimated_hpp=1_000_000)
    assert p.estimated_gross_profit == 1_000_000


def test_negative_margin_when_price_below_hpp():
    p = _project(approved_price=1_000_000, actual_hpp=1_500_000)
    assert p.actual_gross_profit == -500_000
    assert p.actual_gross_margin_pct == -50.0


def test_all_statuses_have_transitions_defined():
    for s in PROJECT_STATUSES:
        assert s in ALLOWED_PROJECT_TRANSITIONS


def test_delivered_is_terminal():
    assert ALLOWED_PROJECT_TRANSITIONS[ProjectStatus.DELIVERED.value] == frozenset()


def test_cancelled_is_terminal():
    assert ALLOWED_PROJECT_TRANSITIONS[ProjectStatus.CANCELLED.value] == frozenset()


def test_terminal_statuses_set():
    assert "DELIVERED" in TERMINAL_PROJECT_STATUSES
    assert "CANCELLED" in TERMINAL_PROJECT_STATUSES
    assert "IN_PROGRESS" not in TERMINAL_PROJECT_STATUSES


def test_draft_can_start_estimating():
    allowed = ALLOWED_PROJECT_TRANSITIONS[ProjectStatus.DRAFT.value]
    assert ProjectStatus.ESTIMATING.value in allowed


def test_in_progress_can_go_to_painting():
    allowed = ALLOWED_PROJECT_TRANSITIONS[ProjectStatus.IN_PROGRESS.value]
    assert ProjectStatus.PAINTING.value in allowed


def test_cost_categories_complete():
    expected = {"MATERIAL", "PART", "LABOR", "OUTSOURCE", "OVERHEAD", "MISC"}
    assert set(COST_CATEGORIES) == expected


def test_cost_category_is_str_enum():
    assert CostCategory.MATERIAL.value == "MATERIAL"