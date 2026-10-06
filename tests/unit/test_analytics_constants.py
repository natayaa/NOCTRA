"""Analytics date-range and interval tests — Phase 7."""

from datetime import date, timedelta

from app.modules.analytics.constants import (
    Interval,
    PERIOD_PRESETS,
    PeriodPreset,
    pick_interval,
    resolve_period,
)


def test_resolve_today():
    f, t = resolve_period("today")
    assert f == t == date.today()


def test_resolve_week():
    f, t = resolve_period("week")
    assert t == date.today()
    assert (t - f).days == 7


def test_resolve_month():
    f, t = resolve_period("month")
    assert (t - f).days == 30


def test_resolve_quarter():
    f, t = resolve_period("quarter")
    assert (t - f).days == 90


def test_resolve_year():
    f, t = resolve_period("year")
    assert (t - f).days == 365


def test_resolve_ytd_starts_jan_1():
    f, t = resolve_period("ytd")
    assert f.month == 1
    assert f.day == 1
    assert f.year == t.year


def test_unknown_preset_defaults_to_month():
    f, t = resolve_period("garbage")
    assert (t - f).days == 30


def test_explicit_dates_override_preset():
    custom_from = date(2025, 1, 1)
    custom_to = date(2025, 12, 31)
    f, t = resolve_period("today", from_date=custom_from, to_date=custom_to)
    assert f == custom_from
    assert t == custom_to


def test_pick_interval_daily_for_short_ranges():
    today = date.today()
    assert pick_interval(today - timedelta(days=10), today) == Interval.DAY.value
    assert pick_interval(today - timedelta(days=30), today) == Interval.DAY.value


def test_pick_interval_weekly_for_medium():
    today = date.today()
    assert pick_interval(today - timedelta(days=90), today) == Interval.WEEK.value


def test_pick_interval_monthly_for_long():
    today = date.today()
    assert pick_interval(today - timedelta(days=365), today) == Interval.MONTH.value


def test_pick_interval_quarterly_for_very_long():
    today = date.today()
    assert pick_interval(today - timedelta(days=1000), today) == Interval.QUARTER.value


def test_period_presets_enum_matches_list():
    assert set(PERIOD_PRESETS) == {p.value for p in PeriodPreset}