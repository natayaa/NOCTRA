# tests/test_inquiry_status.py

import pytest
from core.constants import InquiryStatus
from modules.inquiry.services import ALLOWED_TRANSITIONS


@pytest.mark.asyncio
async def test_status_transition_valid():
    """Test valid transitions."""
    # new → under_review → contacted → quoted → approved → converted → completed
    transitions = [
        (InquiryStatus.NEW, InquiryStatus.UNDER_REVIEW),
        (InquiryStatus.UNDER_REVIEW, InquiryStatus.CONTACTED),
        (InquiryStatus.CONTACTED, InquiryStatus.QUOTED),
        (InquiryStatus.QUOTED, InquiryStatus.APPROVED),
        (InquiryStatus.APPROVED, InquiryStatus.CONVERTED),
        (InquiryStatus.CONVERTED, InquiryStatus.COMPLETED),
    ]

    for old, new in transitions:
        assert new in ALLOWED_TRANSITIONS.get(old, [])


@pytest.mark.asyncio
async def test_status_transition_invalid():
    """Test invalid transitions."""
    # new → completed (langsung tanpa melalui proses)
    assert InquiryStatus.COMPLETED not in ALLOWED_TRANSITIONS.get(
        InquiryStatus.NEW, [])

    # rejected → approved (tidak bisa)
    assert InquiryStatus.APPROVED not in ALLOWED_TRANSITIONS.get(
        InquiryStatus.REJECTED, [])
