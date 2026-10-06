from datetime import datetime
from decimal import Decimal

from jinja2 import Environment


def rupiah(value: int | float | Decimal | None, *, with_symbol: bool = True) -> str:
    if value is None:
        value = 0
    n = int(value)
    formatted = f"{n:,}".replace(",", ".")
    return f"Rp {formatted}" if with_symbol else formatted


def dt_id(value: datetime | None, fmt: str = "%d %b %Y, %H:%M") -> str:
    if value is None:
        return "-"
    return value.strftime(fmt)


def register_filters(templates) -> None:
    env: Environment = templates.env
    env.filters["rupiah"] = rupiah
    env.filters["dt_id"] = dt_id