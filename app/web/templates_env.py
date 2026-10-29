"""Jinja2 templates environment for the admin & public web UI.

Templates are configured with:
- The app's shared filters (`rupiah`, `dt_id`, `date_id`, `pct`, `number`).
- Globals for app metadata, CSRF tokens, and helpers.
- `today()` / `today_local()` that respect `APP_TIMEZONE`, not system TZ.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from starlette.requests import Request

from app.core.config import settings
from app.web.filters import register_filters

APP_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

if not TEMPLATES_DIR.is_dir():
    raise RuntimeError(f"Templates directory not found: {TEMPLATES_DIR}")


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _today_local() -> date:
    """
    Today's date in the app's configured timezone.

    `date.today()` returns the system-local date — wrong on any host whose
    clock is UTC (e.g., container). Between 00:00–07:00 WIB this returns
    "yesterday", which breaks comparisons like
    `{% if project.target_end_date < today() %}`.
    """
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


def _asset_url(path: str) -> str:
    """Cache-busted static URL: /static/<path>?v=<mtime>."""
    rel = path.lstrip("/")
    try:
        version = (STATIC_DIR / rel).stat().st_mtime_ns
    except OSError:
        version = 0
    return f"/static/{rel}?v={version}"


def _csrf_value(request: Request | None) -> str:
    """
    Get the CSRF token for a request.

    Reads `request.state.csrf_token` first (set by CsrfTokenMiddleware).
    Falls back to the cookie — useful in fragments rendered before the
    middleware has run (rare but defensive).
    """
    if request is None:
        return ""
    token = getattr(request.state, "csrf_token", "") or ""
    if not token:
        raw = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
        token = raw.strip('"') if raw else ""
    return token


@pass_context
def _query_string(context, **overrides) -> str:
    """
    Build a query string from the current request, with overrides.

    Filter links need to preserve the other active filters (search terms,
    per-page size, sort). Without this, clicking a status chip on page 3
    silently drops `q` and `per_page`.

    - A non-empty value replaces the parameter.
    - `None`, `""`, or `False` removes it.
    - `True` becomes `"true"` (matches boolean query-param parsing).
    - Always returns a leading `?`, or `""` when no parameters remain.
    """
    request = context.get("request")
    params: dict[str, str] = {}
    if request is not None:
        params.update(request.query_params.multi_items())

    for key, value in overrides.items():
        if value is None or value is False or value == "":
            params.pop(key, None)
        elif value is True:
            params[key] = "true"
        else:
            params[key] = str(value)

    encoded = urlencode(params)
    return f"?{encoded}" if encoded else ""


# Admin navigation map — the single source of truth for breadcrumbs.
# Keep labels in sync with components/sidebar.html. A section may also list
# pages that are reachable from another page (reports, email log) but not
# shown in the sidebar; they still need a proper breadcrumb.
ADMIN_NAV: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Main", (
        ("/admin/dashboard", "Dashboard"),
        ("/admin/inquiries", "Inquiries"),
        ("/admin/customers", "Customers"),
        ("/admin/vehicles", "Vehicles"),
        ("/admin/projects", "Projects"),
    )),
    ("Workshop", (
        ("/admin/inventory", "Inventory"),
        ("/admin/materials", "Materials"),
        ("/admin/purchase-orders", "Purchase Orders"),
        ("/admin/suppliers", "Suppliers"),
        ("/admin/employees", "Employees"),
    )),
    ("Finance", (
        ("/admin/invoices", "Invoices"),
        ("/admin/payments", "Payments"),
        ("/admin/expenses", "Expenses"),
        ("/admin/reports/pnl", "P&L Report"),
        ("/admin/reports/receivables", "Receivables"),
        ("/admin/reports/payables", "Payables"),
        ("/admin/pricing-rules", "Pricing Rules"),
        ("/admin/pricing-analytics", "Pricing Analytics"),
    )),
    ("System", (
        ("/admin/email-logs", "Email Log"),
        ("/admin/users", "Users"),
        ("/admin/roles", "Roles"),
        ("/admin/audit", "Audit Log"),
        ("/admin/settings", "Settings"),
        ("/admin/profile", "Profile"),
    )),
)

# Routes that only ever appear as a leaf below a list page.
_ADMIN_LEAF_LABELS = {
    "new": "New",
    "edit": "Edit",
    "print": "Print",
    "export.csv": "Export",
    "statement": "Statement",
    "transactions": "Stock movements",
    "forgot-password": "Forgot password",
    "reset-password": "Reset password",
}

# Singular noun for detail pages (`/admin/inquiries/<uuid>`).
_ADMIN_DETAIL_LABELS = {
    "/admin/inquiries": "Inquiry",
    "/admin/customers": "Customer",
    "/admin/vehicles": "Vehicle",
    "/admin/projects": "Project",
    "/admin/inventory": "Item",
    "/admin/materials": "Material",
    "/admin/purchase-orders": "Purchase order",
    "/admin/pricing-rules": "Pricing rule",
    "/admin/suppliers": "Supplier",
    "/admin/employees": "Employee",
    "/admin/invoices": "Invoice",
    "/admin/payments": "Payment",
    "/admin/expenses": "Expense",
    "/admin/users": "User",
    "/admin/roles": "Role",
}

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_NUMERIC_RE = re.compile(r"^\d+$")


def _admin_crumbs(path: str | None) -> list[dict[str, str | None]]:
    """Breadcrumbs for an admin path: section → list page → current item.

    Derived from ``ADMIN_NAV`` so the header stays in sync with the
    sidebar. The last crumb is never a link (it is the current page).
    """
    path = (path or "").rstrip("/") or "/"
    if not path.startswith("/admin"):
        return []

    for section, items in ADMIN_NAV:
        for href, label in items:
            if path == href:
                return [
                    {"label": section, "href": None},
                    {"label": label, "href": None},
                ]
            if not path.startswith(href + "/"):
                continue

            rest = path[len(href) + 1:].split("/")
            leaf = rest[-1] if rest else ""
            if leaf in _ADMIN_LEAF_LABELS:
                trailing = _ADMIN_LEAF_LABELS[leaf]
            elif _UUID_RE.match(leaf) or _NUMERIC_RE.match(leaf):
                trailing = _ADMIN_DETAIL_LABELS.get(href, "Detail")
            else:
                trailing = leaf.replace("-", " ").replace("_", " ").capitalize()

            crumbs: list[dict[str, str | None]] = [
                {"label": section, "href": None},
                {"label": label, "href": href},
            ]
            if trailing and trailing != label:
                crumbs.append({"label": trailing, "href": None})
            return crumbs

    fallback = path.rsplit("/", 1)[-1] or "Admin"
    return [
        {"label": "Admin", "href": "/admin/dashboard"},
        {"label": fallback.replace("-", " ").replace("_", " ").capitalize(), "href": None},
    ]



# ════════════════════════════════════════════════════════════════
# TEMPLATES
# ════════════════════════════════════════════════════════════════

class NoctraTemplates(Jinja2Templates):
    """
    Templates class that seeds request-scoped context automatically.

    Every `render()` call guarantees these context keys exist (unless the
    caller overrode them explicitly):
      - current_path   — request.url.path, for active nav highlighting
      - csrf_token     — for `<input name="_csrf">` and `X-CSRF-Token`
      - current_user   — the authenticated user (or None)
      - flash_messages — list of flash dicts (empty until middleware adds them)
    """

    def render(self, request, name, context=None, *, status_code=200):
        ctx = dict(context or {})

        ctx.setdefault("current_path", request.url.path if request else "")
        ctx.setdefault("csrf_token", _csrf_value(request))
        ctx.setdefault(
            "current_user",
            getattr(request.state, "user", None) if request else None,
        )
        ctx.setdefault(
            "flash_messages",
            getattr(request.state, "flashes", []) if request else [],
        )

        return self.TemplateResponse(
            request, name, ctx, status_code=status_code,
        )


templates = NoctraTemplates(directory=str(TEMPLATES_DIR))


# ════════════════════════════════════════════════════════════════
# GLOBALS
# ════════════════════════════════════════════════════════════════

templates.env.globals.update(
    # ── Time ────────────────────────────────────────────
    today=_today_local,
    today_local=_today_local,
    # ── Static assets ───────────────────────────────────
    asset_url=_asset_url,
    # ── URL helpers ─────────────────────────────────────
    qs=_query_string,
    admin_crumbs=_admin_crumbs,
    # ── App metadata ────────────────────────────────────
    app_name=settings.APP_NAME,
    app_env=settings.APP_ENV,
    # Convenience booleans — cleaner than `{% if app_env == "..." %}`.
    app_env_is_production=settings.is_production,
    app_env_is_development=(settings.APP_ENV == "development"),
    # ── CSRF ────────────────────────────────────────────
    csrf_cookie_name=settings.CSRF_COOKIE_NAME,
    csrf_header_name=settings.CSRF_HEADER_NAME,
    csrf_value=_csrf_value,
)


# Filters — imported from filters.py
register_filters(templates)