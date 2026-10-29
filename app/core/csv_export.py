"""CSV export helpers.

Spreadsheet applications treat cells starting with ``=``, ``+``, ``-``,
``@`` (and tab/CR) as formulas. Customer-supplied free text exported to
CSV must not be able to run a formula when an operator opens the file.

Prefixing the cell with a single quote forces Excel/Sheets/LibreOffice
to treat it as text. The quote is not displayed in the cell.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

_DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")
# A leading +/- on a plain number (negative amount) is not a formula, so
# keep it numeric instead of turning "-12.5" into "'-12.5". Anything with
# other characters (e.g. "+62 812-3456") still gets neutralised.
_NUMERIC_RE = re.compile(r"^[+-]\d+(?:[.,]\d+)?$")


def csv_cell(value: Any) -> Any:
    """Neutralise formula-leading strings; leave other values untouched."""
    if not isinstance(value, str):
        return value
    if value.startswith(_DANGEROUS_PREFIXES):
        if (value[0] in "+-") and _NUMERIC_RE.fullmatch(value):
            return value
        return "'" + value
    return value


def csv_safe_row(values: Iterable[Any]) -> list[Any]:
    """Apply :func:`csv_cell` to every value in a row."""
    return [csv_cell(value) for value in values]
