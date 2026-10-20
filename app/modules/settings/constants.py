"""Known setting keys, validators, and cache TTL.

The registry here is the SINGLE SOURCE OF TRUTH for:
  - which setting keys exist
  - what category/description they carry
  - which validator applies to the value
  - whether the value must be redacted in responses/audit

Modules that use a setting (pricing, projects, email) should import the
key from here — not hardcode the string.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


# ── Cache TTL ─────────────────────────────────────────────
# `get_value` results are cached in-process for this long. Values are
# small and change rarely. When a setting is upserted, the cache entry
# is invalidated immediately in the writing process; other workers
# (uvicorn --workers N) will serve stale values for at most TTL seconds.
SETTINGS_CACHE_TTL_SECONDS: int = 60


# ════════════════════════════════════════════════════════════════
# KEYS — grouped by domain
# ════════════════════════════════════════════════════════════════

# Costing — read by projects/pricing modules
KEY_COSTING_OVERHEAD_MONTHLY = "costing.overhead_monthly"
KEY_COSTING_MONTHLY_LABOR_HOURS = "costing.monthly_labor_hours"
KEY_COSTING_DEFAULT_TARGET_MARGIN = "costing.default_target_margin_pct"
KEY_COSTING_MIN_MARGIN = "costing.minimum_margin_pct"

# Email / SMTP — used by email module (phase 2d)
KEY_EMAIL_SMTP_HOST = "email.smtp_host"
KEY_EMAIL_SMTP_PORT = "email.smtp_port"
KEY_EMAIL_SMTP_USERNAME = "email.smtp_username"
KEY_EMAIL_SMTP_PASSWORD = "email.smtp_password"
KEY_EMAIL_FROM_ADDRESS = "email.from_address"

# Public contact info — read by templates
KEY_PUBLIC_PHONE = "public.phone"
KEY_PUBLIC_EMAIL = "public.email"
KEY_PUBLIC_ADDRESS = "public.address"
KEY_PUBLIC_WHATSAPP = "public.whatsapp"


# ════════════════════════════════════════════════════════════════
# VALIDATORS
# ════════════════════════════════════════════════════════════════

def _noop(v: str | None) -> str | None:
    return v


def _numeric(
    *, min_val: float | None = None, max_val: float | None = None, integer: bool = False
) -> Callable[[str | None], str | None]:
    """
    Return a validator that ensures the value parses as a number.
    Empty/None values are allowed (they mean "use default in code").
    """
    def _v(v: str | None) -> str | None:
        if v is None or v == "":
            return v
        try:
            n = int(v) if integer else float(v)
        except (TypeError, ValueError) as exc:
            kind = "an integer" if integer else "a number"
            raise ValueError(f"must be {kind}") from exc
        if min_val is not None and n < min_val:
            raise ValueError(f"must be >= {min_val}")
        if max_val is not None and n > max_val:
            raise ValueError(f"must be <= {max_val}")
        return v
    return _v


def _pct(v: str | None) -> str | None:
    """Percent value in [0, 100) — strictly less than 100."""
    if v is None or v == "":
        return v
    try:
        n = float(v)
    except (TypeError, ValueError) as exc:
        raise ValueError("must be a number") from exc
    if not (0 <= n < 100):
        raise ValueError("must be in [0, 100)")
    return v


# ════════════════════════════════════════════════════════════════
# REGISTRY
# ════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SettingSpec:
    category: str
    description: str
    validate: Callable[[str | None], str | None]
    is_secret: bool = False


KNOWN_SETTINGS: dict[str, SettingSpec] = {
    # ── Costing ─────────────────────────────────────────
    KEY_COSTING_OVERHEAD_MONTHLY: SettingSpec(
        category="costing",
        description="Monthly overhead in IDR (used for hourly overhead rate)",
        validate=_numeric(min_val=0),
    ),
    KEY_COSTING_MONTHLY_LABOR_HOURS: SettingSpec(
        category="costing",
        description="Billable labor hours per month",
        validate=_numeric(min_val=0),
    ),
    KEY_COSTING_DEFAULT_TARGET_MARGIN: SettingSpec(
        category="costing",
        description="Default target margin % (0–99.99)",
        validate=_pct,
    ),
    KEY_COSTING_MIN_MARGIN: SettingSpec(
        category="costing",
        description="Absolute minimum margin % (0–99.99)",
        validate=_pct,
    ),

    # ── Email / SMTP ────────────────────────────────────
    KEY_EMAIL_SMTP_HOST: SettingSpec(
        category="email",
        description="SMTP server hostname",
        validate=_noop,
    ),
    KEY_EMAIL_SMTP_PORT: SettingSpec(
        category="email",
        description="SMTP port (1–65535)",
        validate=_numeric(min_val=1, max_val=65535, integer=True),
    ),
    KEY_EMAIL_SMTP_USERNAME: SettingSpec(
        category="email",
        description="SMTP username",
        validate=_noop,
    ),
    KEY_EMAIL_SMTP_PASSWORD: SettingSpec(
        category="email",
        description="SMTP password (stored encrypted-at-rest by DB)",
        validate=_noop,
        is_secret=True,
    ),
    KEY_EMAIL_FROM_ADDRESS: SettingSpec(
        category="email",
        description="Default From address for outbound email",
        validate=_noop,
    ),

    # ── Public contact info ─────────────────────────────
    KEY_PUBLIC_PHONE: SettingSpec(
        category="public",
        description="Public phone number shown on site",
        validate=_noop,
    ),
    KEY_PUBLIC_EMAIL: SettingSpec(
        category="public",
        description="Public contact email",
        validate=_noop,
    ),
    KEY_PUBLIC_ADDRESS: SettingSpec(
        category="public",
        description="Public physical address",
        validate=_noop,
    ),
    KEY_PUBLIC_WHATSAPP: SettingSpec(
        category="public",
        description="WhatsApp contact number",
        validate=_noop,
    ),
}


def spec_for(key: str) -> SettingSpec | None:
    """Look up a known spec — returns None for custom/unknown keys."""
    return KNOWN_SETTINGS.get(key)


def validate_value(key: str, value: str | None) -> str | None:
    """
    Run the validator for a known key. Unknown keys pass through
    unchanged. Raises ValueError if the value is malformed.
    """
    spec = KNOWN_SETTINGS.get(key)
    if spec is None:
        return value
    return spec.validate(value)


def is_secret_key(key: str) -> bool:
    """True if the key is registered as a secret."""
    spec = KNOWN_SETTINGS.get(key)
    return spec.is_secret if spec else False