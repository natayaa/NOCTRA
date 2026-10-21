"""Known setting keys, validators, and cache TTL.

The registry here is the SINGLE SOURCE OF TRUTH for:
  - which setting keys exist
  - what category/description they carry
  - which validator applies to the value
  - whether the value must be redacted in responses/audit

Modules that use a setting (pricing, projects, email) should import the
key from here — not hardcode the string. `scripts/seed_settings.py`
builds its defaults from this same registry, so a key cannot be seeded
without a spec and cannot be validated differently in two places.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# ── Cache TTL ─────────────────────────────────────────────
# `get_value` results are cached in-process for this long. Values are
# small and change rarely. When a setting is upserted, the cache entry
# is invalidated immediately in the writing process; other workers
# (uvicorn --workers N) will serve stale values for at most TTL seconds.
SETTINGS_CACHE_TTL_SECONDS: int = 60


# ════════════════════════════════════════════════════════════════
# KEYS — grouped by domain
# ════════════════════════════════════════════════════════════════

# Business identity — used by invoices/documents and the admin UI
KEY_BUSINESS_NAME = "business.name"
KEY_BUSINESS_TAGLINE = "business.tagline"
KEY_BUSINESS_ADDRESS = "business.address"
KEY_BUSINESS_PHONE = "business.phone"
KEY_BUSINESS_EMAIL = "business.email"
KEY_BUSINESS_TAX_ID = "business.tax_id"
KEY_BUSINESS_CURRENCY = "business.currency"
KEY_BUSINESS_TIMEZONE = "business.timezone"

# CRM / inquiry defaults
KEY_CRM_LEAD_AUTO_STATUS = "crm.lead_auto_status"
KEY_CRM_INQUIRY_AUTO_ASSIGN = "crm.inquiry_auto_assign"
KEY_CRM_INQUIRY_FOLLOWUP_HOURS = "crm.inquiry_followup_hours"

# Costing — read by projects/pricing modules
KEY_COSTING_OVERHEAD_MONTHLY = "costing.overhead_monthly"
KEY_COSTING_MONTHLY_LABOR_HOURS = "costing.monthly_labor_hours"
KEY_COSTING_DEFAULT_TARGET_MARGIN = "costing.default_target_margin_pct"
KEY_COSTING_DEFAULT_MARKUP = "costing.default_markup_pct"
KEY_COSTING_MIN_MARGIN = "costing.minimum_margin_pct"

# Email / SMTP — used by email module (phase 2d)
KEY_EMAIL_SMTP_HOST = "email.smtp_host"
KEY_EMAIL_SMTP_PORT = "email.smtp_port"
KEY_EMAIL_SMTP_USERNAME = "email.smtp_username"
KEY_EMAIL_SMTP_PASSWORD = "email.smtp_password"
KEY_EMAIL_FROM_ADDRESS = "email.from_address"

# Finance
KEY_FINANCE_INVOICE_PREFIX = "finance.invoice_prefix"
KEY_FINANCE_PAYMENT_TERMS_DAYS = "finance.payment_terms_days"
KEY_FINANCE_TAX_RATE_PCT = "finance.tax_rate_pct"

# Inventory
KEY_INVENTORY_LOW_STOCK_THRESHOLD_PCT = "inventory.low_stock_threshold_pct"
KEY_INVENTORY_WASTE_TOLERANCE_PCT = "inventory.waste_tolerance_pct"

# Notifications — inbox destinations
KEY_NOTIFICATIONS_SALES_EMAIL = "notifications.sales_email"
KEY_NOTIFICATIONS_WORKSHOP_EMAIL = "notifications.workshop_email"

# Public site & intake
KEY_PUBLIC_INQUIRY_ENABLED = "public.inquiry_enabled"
KEY_PUBLIC_INQUIRY_RATE_LIMIT = "public.inquiry_rate_limit_per_hour"
KEY_PUBLIC_AUTO_RESPONSE_ENABLED = "public.auto_response_enabled"
KEY_PUBLIC_AUTO_RESPONSE_SUBJECT = "public.auto_response_subject"
KEY_PUBLIC_PHONE = "public.phone"
KEY_PUBLIC_EMAIL = "public.email"
KEY_PUBLIC_ADDRESS = "public.address"
KEY_PUBLIC_WHATSAPP = "public.whatsapp"


# ════════════════════════════════════════════════════════════════
# VALIDATORS
# ════════════════════════════════════════════════════════════════

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


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
        if not math.isfinite(n):
            raise ValueError("must be a finite number")
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


def _bool(v: str | None) -> str | None:
    """Boolean value, normalized to the strings the UI submits."""
    if v is None or v == "":
        return v
    normalized = v.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return "true"
    if normalized in {"false", "0", "no", "off"}:
        return "false"
    raise ValueError("must be true or false")


def _email(v: str | None) -> str | None:
    if v is None or v == "":
        return v
    if not _EMAIL_RE.match(v.strip()):
        raise ValueError("must be a valid email address")
    return v.strip()


def _currency(v: str | None) -> str | None:
    if v is None or v == "":
        return v
    normalized = v.strip().upper()
    if not _CURRENCY_RE.match(normalized):
        raise ValueError("must be a 3-letter currency code")
    return normalized


def _timezone(v: str | None) -> str | None:
    if v is None or v == "":
        return v
    try:
        ZoneInfo(v)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("must be a valid IANA timezone") from exc
    return v


def _one_of(*allowed: str) -> Callable[[str | None], str | None]:
    allowed_set = frozenset(allowed)

    def _v(v: str | None) -> str | None:
        if v is None or v == "":
            return v
        if v not in allowed_set:
            options = ", ".join(sorted(allowed_set))
            raise ValueError(f"must be one of: {options}")
        return v
    return _v


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
    # ── Business identity ───────────────────────────────
    KEY_BUSINESS_NAME: SettingSpec(
        category="business",
        description="Legal business name used on documents",
        validate=_noop,
    ),
    KEY_BUSINESS_TAGLINE: SettingSpec(
        category="business",
        description="Short tagline shown on invoices and the public site",
        validate=_noop,
    ),
    KEY_BUSINESS_ADDRESS: SettingSpec(
        category="business",
        description="Workshop address used on invoices",
        validate=_noop,
    ),
    KEY_BUSINESS_PHONE: SettingSpec(
        category="business",
        description="Business phone number used on documents",
        validate=_noop,
    ),
    KEY_BUSINESS_EMAIL: SettingSpec(
        category="business",
        description="Business email used on documents",
        validate=_email,
    ),
    KEY_BUSINESS_TAX_ID: SettingSpec(
        category="business",
        description="NPWP / tax identification number",
        validate=_noop,
    ),
    KEY_BUSINESS_CURRENCY: SettingSpec(
        category="business",
        description="Default currency code (ISO 4217)",
        validate=_currency,
    ),
    KEY_BUSINESS_TIMEZONE: SettingSpec(
        category="business",
        description="Operational timezone (IANA name)",
        validate=_timezone,
    ),

    # ── CRM ─────────────────────────────────────────────
    KEY_CRM_LEAD_AUTO_STATUS: SettingSpec(
        category="crm",
        description="Status assigned to new customers from public intake",
        validate=_one_of("LEAD", "ACTIVE", "INACTIVE", "BLOCKED"),
    ),
    KEY_CRM_INQUIRY_AUTO_ASSIGN: SettingSpec(
        category="crm",
        description="Auto-assign inquiries to the sales team round-robin",
        validate=_bool,
    ),
    KEY_CRM_INQUIRY_FOLLOWUP_HOURS: SettingSpec(
        category="crm",
        description="Hours before an uncontacted inquiry is flagged",
        validate=_numeric(min_val=1, integer=True),
    ),

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
    KEY_COSTING_DEFAULT_MARKUP: SettingSpec(
        category="costing",
        description="Default markup percentage applied to HPP",
        validate=_numeric(min_val=0),
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
        validate=_email,
    ),

    # ── Finance ─────────────────────────────────────────
    KEY_FINANCE_INVOICE_PREFIX: SettingSpec(
        category="finance",
        description="Prefix for generated invoice numbers",
        validate=_noop,
    ),
    KEY_FINANCE_PAYMENT_TERMS_DAYS: SettingSpec(
        category="finance",
        description="Default payment terms in days",
        validate=_numeric(min_val=0, integer=True),
    ),
    KEY_FINANCE_TAX_RATE_PCT: SettingSpec(
        category="finance",
        description="Default VAT/PPN percentage (0–100)",
        validate=_numeric(min_val=0, max_val=100),
    ),

    # ── Inventory ───────────────────────────────────────
    KEY_INVENTORY_LOW_STOCK_THRESHOLD_PCT: SettingSpec(
        category="inventory",
        description="Flag materials below this % of their minimum stock",
        validate=_numeric(min_val=0, max_val=100),
    ),
    KEY_INVENTORY_WASTE_TOLERANCE_PCT: SettingSpec(
        category="inventory",
        description="Acceptable material waste percentage per project",
        validate=_numeric(min_val=0, max_val=100),
    ),

    # ── Notifications ───────────────────────────────────
    KEY_NOTIFICATIONS_SALES_EMAIL: SettingSpec(
        category="notifications",
        description="Inbox notified about new inquiries",
        validate=_email,
    ),
    KEY_NOTIFICATIONS_WORKSHOP_EMAIL: SettingSpec(
        category="notifications",
        description="Inbox notified about project status changes",
        validate=_email,
    ),

    # ── Public site & intake ────────────────────────────
    KEY_PUBLIC_INQUIRY_ENABLED: SettingSpec(
        category="public",
        description="Whether the public inquiry form accepts submissions",
        validate=_bool,
    ),
    KEY_PUBLIC_INQUIRY_RATE_LIMIT: SettingSpec(
        category="public",
        description="Max inquiries per IP per hour",
        validate=_numeric(min_val=1, integer=True),
    ),
    KEY_PUBLIC_AUTO_RESPONSE_ENABLED: SettingSpec(
        category="public",
        description="Send a confirmation email to inquiry submitters",
        validate=_bool,
    ),
    KEY_PUBLIC_AUTO_RESPONSE_SUBJECT: SettingSpec(
        category="public",
        description="Subject line for the auto-response email",
        validate=_noop,
    ),
    KEY_PUBLIC_PHONE: SettingSpec(
        category="public",
        description="Public phone number shown on the website",
        validate=_noop,
    ),
    KEY_PUBLIC_EMAIL: SettingSpec(
        category="public",
        description="Public contact email shown on the website",
        validate=_email,
    ),
    KEY_PUBLIC_ADDRESS: SettingSpec(
        category="public",
        description="Public physical address shown on the website",
        validate=_noop,
    ),
    KEY_PUBLIC_WHATSAPP: SettingSpec(
        category="public",
        description="Public WhatsApp contact number",
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
