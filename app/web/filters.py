"""Jinja2 template filters — formatting helpers for ID-style output.

Key contracts:
- All datetime filters render in `settings.APP_TIMEZONE` (default Jakarta),
  never in UTC or system-local time.
- All number formats use Indonesian conventions (dot thousand separator,
  comma decimal).
- All format helpers are safe against None/empty/string inputs — templates
  must not crash on user-provided data.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from jinja2 import Environment

from app.core.config import settings


# Indonesian month names — used to replace `%b` / `%B` output from
# strftime (which is always English regardless of system locale).
_MONTHS_ID_SHORT: dict[int, str] = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
    7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des",
}
_MONTHS_ID_LONG: dict[int, str] = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}

# Time tokens that should trigger a date-only fallback when a `date`
# (not `datetime`) is passed to `dt_id`. Different Python versions raise
# (3.12+) or return `"00"` (older) for these — neither is acceptable.
_TIME_TOKENS = ("%H", "%M", "%S", "%p", "%I", "%f")


# ════════════════════════════════════════════════════════════════
# INTERNALS
# ════════════════════════════════════════════════════════════════

def _to_local(dt: datetime) -> datetime:
    """Convert an aware datetime to the app timezone; naive is assumed UTC."""
    tz = ZoneInfo(settings.APP_TIMEZONE)
    if dt.tzinfo is None:
        # Treat naive as UTC — matches how SQLAlchemy `timestamptz` behaves
        # when round-tripping through some drivers. Defensive, not default.
        return dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
    return dt.astimezone(tz)


def _coerce_decimal(value) -> Decimal | None:
    """Best-effort Decimal conversion. Returns None on failure."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _format_thousands(n: int) -> str:
    """`1234567` → `'1.234.567'` (Indonesian convention)."""
    return f"{n:,}".replace(",", ".")


def _apply_id_months(value: date, result: str) -> str:
    """
    Replace English month names in `result` with Indonesian.

    `strftime` uses the C locale by default — `%b` always yields English
    (`Jan`, `May`, ...). We compute English names, then string-replace the
    first occurrence with the corresponding Indonesian name.

    Caveat: if the caller uses a custom literal containing "Jan" / "May"
    in the format string, it will also be replaced. This is documented and
    acceptable for our templates (no custom month literals in practice).
    """
    long_en = value.strftime("%B")    # e.g. "January"
    short_en = value.strftime("%b")   # e.g. "Jan"
    # Replace long form first — "January" contains "Jan".
    result = result.replace(long_en, _MONTHS_ID_LONG[value.month])
    result = result.replace(short_en, _MONTHS_ID_SHORT[value.month])
    return result


# ════════════════════════════════════════════════════════════════
# MONEY
# ════════════════════════════════════════════════════════════════

def rupiah(
    value: int | float | Decimal | str | None,
    *,
    with_symbol: bool = True,
    decimals: int = 0,
) -> str:
    """
    Format a money value as Rupiah with Indonesian conventions.

    - Rounds half-up (money convention) — not truncated.
    - Accepts int / float / Decimal / string; unknown values become 0.
    - Negative values keep the minus sign before the digits.

    Examples:
        rupiah(1500)                    -> "Rp 1.500"
        rupiah(1500.5)                  -> "Rp 1.501"    (half-up)
        rupiah(Decimal("1500.49"))      -> "Rp 1.500"
        rupiah(-500)                    -> "Rp -500"
        rupiah(1500, with_symbol=False) -> "1.500"
        rupiah(1234.5678, decimals=2)   -> "Rp 1.234,57"
    """
    d = _coerce_decimal(value)
    if d is None:
        d = Decimal(0)

    if decimals > 0:
        q = d.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
        whole_s, _, frac_s = f"{q:f}".partition(".")
        negative = whole_s.startswith("-")
        whole = _format_thousands(int(whole_s.lstrip("-")))
        formatted = f"-{whole}" if negative else whole
        if frac_s:
            formatted = f"{formatted},{frac_s}"
    else:
        n = int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        formatted = _format_thousands(n)

    return f"Rp {formatted}" if with_symbol else formatted


def number(value: int | float | Decimal | None) -> str:
    """
    Format an integer count with `.` thousand separator (ID convention).

    Truncates towards zero — safe for float-to-int conversions where the
    caller expects an integer count (avoids the "1499.9999 → 1500" issue).
    """
    d = _coerce_decimal(value)
    if d is None:
        d = Decimal(0)
    return _format_thousands(int(d))


def pct(
    value: int | float | Decimal | None,
    *,
    digits: int = 1,
) -> str:
    """
    Format a percentage. Uses comma decimal separator.

    Examples:
        pct(63.452)              -> "63,5%"
        pct(63.452, digits=2)    -> "63,45%"
        pct(0)                   -> "0,0%"
    """
    d = _coerce_decimal(value)
    if d is None:
        d = Decimal(0)
    q = d.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)
    s = f"{q:f}"
    if "." in s:
        s = s.replace(".", ",")
    return f"{s}%"


# ════════════════════════════════════════════════════════════════
# DATES / DATETIMES
# ════════════════════════════════════════════════════════════════

def dt_id(
    value: datetime | date | None,
    fmt: str = "%d %b %Y, %H:%M",
) -> str:
    """
    Format a datetime in the app timezone (default: Asia/Jakarta).

    - Aware datetimes are converted to the app timezone before formatting.
    - Naive datetimes are assumed UTC (defensive, matches DB convention).
    - If `date` (not `datetime`) is passed and the format contains a time
      token, the format falls back to `%d %b %Y` — prevents Python 3.12+
      `ValueError` on `date.strftime("%H")`.
    - `%b` / `%B` are translated to Indonesian month names.

    Examples:
        dt_id(datetime(2026, 1, 15, 10, 30, tzinfo=UTC))
        -> "15 Jan 2026, 17:30"     (Jakarta = UTC+7)
    """
    if value is None:
        return "—"

    if isinstance(value, datetime):
        local = _to_local(value)
        return _apply_id_months(local, local.strftime(fmt))

    if isinstance(value, date):
        if any(tok in fmt for tok in _TIME_TOKENS):
            fmt = "%d %b %Y"
        return _apply_id_months(value, value.strftime(fmt))

    return str(value)


def date_id(
    value: date | datetime | None,
    fmt: str = "%d %b %Y",
) -> str:
    """
    Format a date-only value (no time component).

    Examples:
        date_id(date(2026, 1, 15))                    -> "15 Jan 2026"
        date_id(date(2026, 8, 15), "%d %B %Y")        -> "15 Agustus 2026"
    """
    if value is None:
        return "—"

    if isinstance(value, datetime):
        value = _to_local(value).date()

    return _apply_id_months(value, value.strftime(fmt))

def qty(
    value: int | float | Decimal | str | None,
    *,
    decimals: int = 2,
) -> str:
    """
    Format a stock quantity with Indonesian conventions.

    - Dot as thousands separator, comma as decimal separator.
    - Trailing zeros after decimal are trimmed (except when value is 0).
    - Handles negative values (signed ledger entries).
    - Safe against None/string inputs.

    Examples:
        qty(1000)            -> "1.000"
        qty(1000.5)          -> "1.000,5"
        qty(0.05)            -> "0,05"
        qty(-5.1234, decimals=4) -> "-5,1234"
        qty(None)            -> "0"
    """
    d = _coerce_decimal(value)
    if d is None:
        d = Decimal(0)

    q = d.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    q_abs = abs(q)
    s = f"{q_abs:f}"

    if "." in s:
        whole, _, frac = s.partition(".")
        frac = frac.rstrip("0")
        whole_sep = _format_thousands(int(whole))
        if not frac:
            return f"{sign}{whole_sep}"
        return f"{sign}{whole_sep},{frac}"

    return f"{sign}{_format_thousands(int(s))}"

# ════════════════════════════════════════════════════════════════
# REGISTRATION
# ════════════════════════════════════════════════════════════════

def register_filters(templates) -> None:
    env: Environment = templates.env
    env.filters["rupiah"] = rupiah
    env.filters["number"] = number
    env.filters["pct"] = pct
    env.filters["qty"] = qty  
    env.filters["dt_id"] = dt_id
    env.filters["date_id"] = date_id