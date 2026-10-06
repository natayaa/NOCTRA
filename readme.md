# NOCTRA Autoworks

> A business management platform for a motorcycle refinishing and restoration workshop.
> Built from the ground up to answer the question every workshop owner asks:
> **"Motor ini dijual Rp X, sebenarnya HPP-nya berapa, margin saya berapa, dan uang saya habis di mana?"**

NOCTRA is not a CRUD app. It's a decision system for the business — every job's actual cost is tracked,
every material movement is logged, and every project's profitability is computable in real time.

---

## Status

| Phase | Scope | Status |
|---|---|---|
| **1** | Foundation — auth, RBAC, audit, settings, admin shell | ✅ Complete |
| **2a** | CRM — Customers + Vehicles | ✅ Complete |
| **2b** | CRM — Inquiries with rich customer-request capture | ✅ Complete |
| **2c** | Public — Website inquiry intake form | ✅ Complete |
| **2d** | Notifications — Email auto-response + sales alerts | ✅ Complete |
| **3** | Inventory — Materials, stock ledger, purchase orders | ✅ Complete |
| **4** | Costing Engine — Projects, HPP, estimated vs actual | ✅ Complete |
| 5 | Pricing Engine — Margin/markup rules, price recommendations | 📋 Planned |
| 6 | Finance — Payments, receivables, P&L | 📋 Planned |
| 7 | Analytics — Dashboards, profitability trends | 📋 Planned |

---

## What It Does

### For customers
- Public landing page with service catalog and portfolio
- Inquiry form at `/contact` — submits name, vehicle, service, color/finish preferences, photos
- Instant auto-response email confirming receipt with a reference number

### For the sales team
- Every website inquiry appears in `/admin/inquiries` within seconds
- Rich CRM with status workflow: `NEW → CONTACTED → QUOTED → NEGOTIATING → APPROVED → CONVERTED`
- Assignment, follow-up tracking, closing notes
- Customer and vehicle history, one click away

### For the workshop
- Material and part inventory with full transaction ledger
- Purchase orders from suppliers
- Project dashboard showing active work
- Per-project cost capture: materials used, labor hours, outsourcing, overhead allocation

### For the owner
- **Actual HPP** per project, broken into 6 cost categories
- **Estimated vs actual** side-by-side — see where you overran
- **Live gross margin** — before you commit to the price
- Material consumption across all projects, by month
- Which service types are most profitable
- Full audit trail of every action

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Web framework | **FastAPI** | Async-native, type-safe, great for a monolith that can grow |
| ORM | **SQLAlchemy 2.x (async)** | Modern, expression-based, no magic |
| Database | **PostgreSQL** | JSONB, generated columns, full-text, window functions |
| Migrations | **Alembic** | Async-aware, safe rollback |
| Validation | **Pydantic v2** | Fast, strict, integrates cleanly with FastAPI |
| Templates | **Jinja2 + HTMX** | Server-rendered, no build step, no SPA overhead |
| Styling | **Tailwind CSS (CDN for dev)** | Utility-first, no build pipeline needed yet |
| Passwords | **bcrypt** (direct) | passlib is unmaintained; bcrypt direct is the modern way |
| JWT | **python-jose** | HS256, short-lived access + refresh tokens |
| Logging | **structlog** | JSON in production, pretty in dev, request_id everywhere |
| Rate limiting | **In-process sliding window** | Sufficient until scaling; swap for Redis later |
| Jobs | **In-process async queue** | Fire-and-forget for emails; swap for Arq/Dramatiq later |
| Testing | **pytest + pytest-asyncio + httpx** | Async-first |
| Lint | **ruff** | Fast, replaces flake8/isort/pyupgrade |

---

## Architecture

NOCTRA is a **modular monolith** — one deployable, internally separated into domain modules.
