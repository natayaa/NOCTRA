"""Inquiry workflow transitions — Phase 2b."""

from app.modules.inquiries.constants import (
    ALLOWED_TRANSITIONS,
    BUDGET_LABELS,
    COLOR_LABELS,
    FINISH_LABELS,
    FINISH_TYPES,
    INQUIRY_STATUSES,
    PREFERENCE_KEYS,
    SERVICE_INTERESTS,
    SERVICE_INTEREST_LABELS,
    TERMINAL_STATUSES,
    InquiryStatus,
)


def test_terminal_statuses():
    assert InquiryStatus.CONVERTED.value in TERMINAL_STATUSES
    assert InquiryStatus.LOST.value in TERMINAL_STATUSES
    assert InquiryStatus.NEW.value not in TERMINAL_STATUSES


def test_new_can_go_to_contacted_or_lost():
    allowed = ALLOWED_TRANSITIONS[InquiryStatus.NEW.value]
    assert InquiryStatus.CONTACTED.value in allowed
    assert InquiryStatus.LOST.value in allowed
    assert InquiryStatus.QUOTED.value not in allowed


def test_contacted_can_go_to_quoted_or_lost():
    allowed = ALLOWED_TRANSITIONS[InquiryStatus.CONTACTED.value]
    assert InquiryStatus.QUOTED.value in allowed
    assert InquiryStatus.LOST.value in allowed


def test_quoted_can_negotiate_approve_or_lose():
    allowed = ALLOWED_TRANSITIONS[InquiryStatus.QUOTED.value]
    assert InquiryStatus.NEGOTIATING.value in allowed
    assert InquiryStatus.APPROVED.value in allowed
    assert InquiryStatus.LOST.value in allowed


def test_negotiating_can_approve_or_lose():
    allowed = ALLOWED_TRANSITIONS[InquiryStatus.NEGOTIATING.value]
    assert InquiryStatus.APPROVED.value in allowed
    assert InquiryStatus.LOST.value in allowed


def test_approved_can_convert_or_lose():
    allowed = ALLOWED_TRANSITIONS[InquiryStatus.APPROVED.value]
    assert InquiryStatus.CONVERTED.value in allowed
    assert InquiryStatus.LOST.value in allowed


def test_converted_is_terminal():
    assert ALLOWED_TRANSITIONS[InquiryStatus.CONVERTED.value] == frozenset()


def test_lost_is_terminal():
    assert ALLOWED_TRANSITIONS[InquiryStatus.LOST.value] == frozenset()


def test_all_statuses_have_transitions_defined():
    for status in INQUIRY_STATUSES:
        assert status in ALLOWED_TRANSITIONS


def test_cannot_skip_from_new_to_converted():
    allowed = ALLOWED_TRANSITIONS[InquiryStatus.NEW.value]
    assert InquiryStatus.CONVERTED.value not in allowed


def test_finish_types_include_common_values():
    for f in ("GLOSS", "SATIN", "MATTE", "DOFF", "WET_GLOSS"):
        assert f in FINISH_TYPES


def test_finish_labels_cover_all_types():
    for f in FINISH_TYPES:
        assert f in FINISH_LABELS


def test_color_labels_cover_common_colors():
    for c in ("BLACK", "WHITE", "RED", "SILVER", "GOLD"):
        assert c in COLOR_LABELS


def test_budget_labels():
    for b in ("UNDER_1M", "R1_3M", "R3_5M", "R5_10M"):
        assert b in BUDGET_LABELS


def test_service_interests_have_labels():
    for s in SERVICE_INTERESTS:
        assert s in SERVICE_INTEREST_LABELS


def test_preference_keys_are_well_formed():
    assert len(PREFERENCE_KEYS) > 0
    for pk in PREFERENCE_KEYS:
        assert "key" in pk
        assert "label" in pk
        assert "type" in pk
        assert pk["type"] in ("bool", "list", "string", "text", "json")