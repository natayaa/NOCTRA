"""Analytics module constants."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from app.core.config import settings


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


def _today_local() -> date:
    """Today's date in the app's configured timezone (not UTC)."""
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


def resolve_period(
    preset: str,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[date, date]:
    """
    Resolve a preset name into a concrete (from, to) date range.

    Both from_date AND to_date must be provided to override the preset;
    providing only one raises ValueError so callers can return 400.
    Presets are inclusive — "Last 7 days" covers exactly 7 calendar days.
    """
    # Explicit override path
    if from_date is not None and to_date is not None:
        if from_date > to_date:
            raise ValueError("from_date must be <= to_date")
        return from_date, to_date

    if (from_date is None) != (to_date is None):
        raise ValueError("Provide both from_date and to_date, or neither")

    today = _today_local()

    if preset == PeriodPreset.TODAY.value:
        return today, today
    if preset == PeriodPreset.WEEK.value:
        return today - timedelta(days=6), today      # 7 days inclusive
    if preset == PeriodPreset.MONTH.value:
        return today - timedelta(days=29), today     # 30 days inclusive
    if preset == PeriodPreset.QUARTER.value:
        return today - timedelta(days=89), today     # 90 days inclusive
    if preset == PeriodPreset.YEAR.value:
        return today - timedelta(days=364), today    # 365 days inclusive
    if preset == PeriodPreset.YTD.value:
        return today.replace(month=1, day=1), today

    raise ValueError(f"Unknown period preset: {preset!r}")


def pick_interval(from_date: date, to_date: date) -> str:
    """Auto-pick a sensible interval based on the range span."""
    days = (to_date - from_date).days
    if days <= 31:
        return Interval.DAY.value
    if days <= 120:
        return Interval.WEEK.value
    if days <= 730:
        return Interval.MONTH.value
    return Interval.QUARTER.value