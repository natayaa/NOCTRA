"""Central import point for all SQLAlchemy models.

Import this module once before any ORM use so every mapper
is registered and string relationship targets resolve correctly.
"""

from __future__ import annotations

# ── Phase 1 ───────────────────────────────────────────
from app.modules.auth import models as _auth_models          # noqa: F401
from app.modules.rbac import models as _rbac_models          # noqa: F401
from app.modules.audit import models as _audit_models        # noqa: F401
from app.modules.settings import models as _settings_models  # noqa: F401

# ── Phase 2a ──────────────────────────────────────────
from app.modules.customers import models as _customer_models  # noqa: F401
from app.modules.vehicles import models as _vehicle_models    # noqa: F401

# ── Phase 2b ──────────────────────────────────────────
from app.modules.inquiries import models as _inquiry_models    # noqa: F401

# ── Phase 2d ──────────────────────────────────────────
from app.modules.email import models as _email_models  # noqa: F401

# ── Phase 3 ───────────────────────────────────────────
from app.modules.inventory import models as _inventory_models  # noqa: F401

# ── Phase 4 ───────────────────────────────────────────
from app.modules.projects import models as _project_models  # noqa: F401

# ── Phase 5 ───────────────────────────────────────────
from app.modules.pricing import models as _pricing_models  # noqa: F401

# ── Phase 6 ───────────────────────────────────────────
from app.modules.finance import models as _finance_models  # noqa: F401

__all__: list[str] = []