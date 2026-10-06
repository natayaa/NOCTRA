"""Analytics module constants."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from enum import StrEnum


class Interval(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class PeriodPreset(StrEnum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    YTD = "ytd"


INTERVALS: list[str] = [i.value for i in Interval]
PERIOD_PRESETS: list[str] = [p.value for p in PeriodPreset]


PERIOD_LABELS: dict[str, str] = {
    PeriodPreset.TODAY.value:   "Today",
    PeriodPreset.WEEK.value:    "Last 7 days",
    PeriodPreset.MONTH.value:   "Last 30 days",
    PeriodPreset.QUARTER.value: "Last 90 days",
    PeriodPreset.YEAR.value:    "Last 12 months",
    PeriodPreset.YTD.value:     "Year to date",
}

INTERVAL_LABELS: dict[str, str] = {
    Interval.DAY.value:     "Daily",
    Interval.WEEK.value:    "Weekly",
    Interval.MONTH.value:   "Monthly",
    Interval.QUARTER.value: "Quarterly",
    Interval.YEAR.value:    "Yearly",
}


def resolve_period(
    preset: str,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[date, date]:
    """
    Resolve a preset name into a concrete (from, to) date range.
    If both from/to are provided, they override the preset.
    """
    if from_date and to_date:
        return from_date, to_date

    today = datetime.now(UTC).date()

    if preset == PeriodPreset.TODAY.value:
        return today, today
    if preset == PeriodPreset.WEEK.value:
        return today - timedelta(days=7), today
    if preset == PeriodPreset.MONTH.value:
        return today - timedelta(days=30), today
    if preset == PeriodPreset.QUARTER.value:
        return today - timedelta(days=90), today
    if preset == PeriodPreset.YEAR.value:
        return today - timedelta(days=365), today
    if preset == PeriodPreset.YTD.value:
        return today.replace(month=1, day=1), today

    # Fallback
    return today - timedelta(days=30), today


def pick_interval(from_date: date, to_date: date) -> str:
    """Auto-pick a sensible interval based on the range span."""
    days = (to_date - from_date).days
    if days <= 1:
        return Interval.DAY.value
    if days <= 31:
        return Interval.DAY.value
    if days <= 120:
        return Interval.WEEK.value
    if days <= 730:
        return Interval.MONTH.value
    return Interval.QUARTER.value