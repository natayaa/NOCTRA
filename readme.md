# NOCTRA Autoworks

> A business management platform for a motorcycle refinishing and restoration workshop.
>
> Built to answer the question every workshop owner asks:
> **"Motor ini dijual Rp X — HPP-nya berapa, margin saya berapa, dan uangnya habis di mana?"**

NOCTRA is not just a CRUD app. It is a decision system: every job's cost is captured,
every material movement is logged, and each project's profitability is visible in real time.

---

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation — auth, RBAC, audit log, settings, admin shell | ✅ Complete |
| 2 | CRM — customers, vehicles, inquiries, public intake | ✅ Complete |
| 3 | Inventory — materials, suppliers, stock ledger, purchase orders | ✅ Complete |
| 4 | Costing — projects, estimated vs actual HPP, labor and overhead | ✅ Complete |
| 5 | Pricing — margin/markup rules and price recommendations | ✅ Implemented |
| 6 | Finance — invoices, payments, expenses, receivables/payables, P&L | ✅ Implemented |
| 7 | Analytics — dashboards and profitability reporting | ✅ Implemented |

"Implemented" means the module, API, admin pages, and migrations exist; reporting depth
continues to evolve.

---

## Highlights

**For customers**
- Public site with service catalog, portfolio, and workshop information
- Inquiry form with vehicle details, service/color/finish preferences, and up to 5 photos
- Instant email acknowledgment with a reference number

**For sales**
- Inquiries land in `/admin/inquiries` with a status workflow:
  `NEW → CONTACTED → QUOTED → NEGOTIATING → APPROVED → CONVERTED`
- Assignment, follow-up tracking, and customer/vehicle history in one place

**For the workshop**
- Materials, suppliers, and a complete stock transaction ledger
- Purchase orders and project dashboards
- Per-project cost capture: materials, labor, outsourcing, overhead

**For the owner**
- Actual HPP per project, split into cost categories
- Estimated vs actual comparison and live gross margin
- Pricing rules by service type and vehicle category, with margin floors
- Invoices, payments, expenses, receivables/payables, and P&L reports
- Full audit trail of sensitive actions

---

## Tech stack

| Layer | Choice |
|---|---|
| Web framework | FastAPI (async) |
| ORM | SQLAlchemy 2.x async + asyncpg |
| Database | PostgreSQL |
| Migrations | Alembic |
| Validation | Pydantic v2 + pydantic-settings |
| Templates | Jinja2 + HTMX |
| Styling | Tailwind CSS (CDN) + custom CSS |
| Auth | JWT (`python-jose`), bcrypt, CSRF double-submit cookies |
| Email | aiosmtplib with retries and an email log |
| Logging | structlog (console or JSON) |
| Tests | pytest, pytest-asyncio, httpx |

---

## Project structure

```text
NOCTRA/
├── app/
│   ├── core/                 # config, database, security, middleware, logging
│   ├── modules/              # domain modules
│   │   ├── auth/             # login, tokens, lockout
│   │   ├── rbac/             # roles and permissions
│   │   ├── users/
│   │   ├── audit/
│   │   ├── settings/         # DB-backed settings + registry
│   │   ├── customers/
│   │   ├── vehicles/
│   │   ├── inquiries/
│   │   ├── inventory/        # materials, suppliers, stock, POs
│   │   ├── projects/         # projects, employees, costing
│   │   ├── pricing/
│   │   ├── finance/          # invoices, payments, expenses, reports
│   │   ├── analytics/
│   │   └── email/
│   ├── services/             # cross-module services (notifications, public intake)
│   ├── web/                  # HTML routes (admin/ and public/)
│   ├── templates/            # Jinja2: admin, public, components, emails
│   └── static/               # CSS, JS, images
├── alembic/                  # migrations (see alembic/README.md)
├── deploy/
│   ├── docker/entrypoint.sh  # wait for DB → migrate → exec app
│   └── nginx/                # reverse proxy config + TLS example
├── scripts/                  # seeding, bootstrap, migration and env helpers
├── tests/                    # unit + integration tests
├── .env.example              # environment template for local development
├── .env.docker.example       # environment template for Docker Compose
├── alembic.ini
├── Dockerfile                # multi-stage, non-root runtime image
├── docker-compose.yml        # app + PostgreSQL + nginx
├── Makefile
├── requirements.txt
└── readme.md
```

---

## Requirements

- **Python 3.11+** (developed on 3.13)
- **PostgreSQL 13+** (14+ recommended)
- `psql` on `PATH` for database creation
- **GNU Make** — optional; every target has a plain command equivalent
- **Docker Engine/Desktop 24+ with Compose v2** — only for the container stack
- On Windows, run commands from **Git Bash**. If `make` is not on `PATH`, use
  `mingw32-make` or the plain commands below.

---

## Quick start

### 1. Create and activate a virtual environment

```bash
python -m venv venv
```

| Shell | Activate |
|---|---|
| PowerShell | `venv\Scripts\Activate.ps1` |
| cmd.exe | `venv\Scripts\activate.bat` |
| Git Bash | `source venv/Scripts/activate` |
| macOS / Linux | `source venv/bin/activate` |

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Or, if Make is available:

```bash
make install
```

### 3. Create the environment file

```bash
cp .env.example .env        # Windows cmd: copy .env.example .env
```

Generate a signing key and put it in `APP_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then edit `.env` and set:

- `APP_SECRET_KEY` — the generated value
- `POSTGRES_PASSWORD` — your local PostgreSQL password
- `APP_BASE_URL` — usually `http://127.0.0.1:8000` in development

The placeholder values in `.env.example` are intentionally rejected by the config
validators, so a half-configured environment fails at startup instead of running insecurely.

### 4. Create the databases

```bash
psql -U postgres -c 'CREATE DATABASE "NOCTRADB" OWNER postgres;'
psql -U postgres -c 'CREATE DATABASE "NOCTRADB_test" OWNER postgres;'
```

The test database is only needed to run pytest.

### 5. Apply migrations

```bash
python -m alembic upgrade head
```

### 6. Seed reference data and create the first user

```bash
python -m scripts.seed_all
python -m scripts.create_superuser
```

`seed_all` is idempotent and never overwrites values edited by operators.
`create_superuser` prompts interactively for username, email, full name, and password.

### 7. Run

```bash
python -m uvicorn app.main:app --reload
```

Open:

| URL | Description |
|---|---|
| http://127.0.0.1:8000/ | Public website |
| http://127.0.0.1:8000/admin/login | Admin login |
| http://127.0.0.1:8000/admin | Admin dashboard |
| http://127.0.0.1:8000/api/docs | OpenAPI docs (disabled in production) |
| http://127.0.0.1:8000/healthz | Liveness probe |
| http://127.0.0.1:8000/readyz | Readiness probe (checks the DB) |

---

## Configuration

All settings are defined in [`app/core/config.py`](app/core/config.py) and loaded from `.env`.
[`.env.example`](.env.example) is the complete, commented reference.

| Group | Variables | Notes |
|---|---|---|
| Application | `APP_NAME`, `APP_ENV`, `APP_DEBUG`, `APP_SECRET_KEY`, `APP_BASE_URL`, `APP_TIMEZONE`, `APP_LOG_LEVEL`, `APP_LOG_FORMAT` | `APP_SECRET_KEY` must be at least 32 characters |
| Database | `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_ECHO` | Tests use `<POSTGRES_DB>_test` |
| Auth | `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `JWT_ALGORITHM`, `JWT_ISSUER`, `BCRYPT_ROUNDS` | HMAC algorithms only |
| Session / CSRF | `SESSION_COOKIE_*`, `SESSION_MAX_AGE_SECONDS`, `CSRF_COOKIE_NAME`, `CSRF_HEADER_NAME`, `CSRF_TOKEN_BYTES` | `SameSite=None` requires a secure cookie |
| Network | `CORS_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `TRUSTED_HOSTS`, `TRUST_PROXY_HEADERS` | Comma-separated lists |
| Rate limits | `RATE_LIMIT_ENABLED`, `RATE_LIMIT_LOGIN_PER_MINUTE`, `RATE_LIMIT_API_PER_MINUTE`, `RATE_LIMIT_PUBLIC_PER_MINUTE` | In-process, per worker |
| Email | `EMAIL_ENABLED`, `EMAIL_FROM_*`, `SMTP_*`, `SMTP_MAX_RETRIES`, `SMTP_RETRY_*` | Disabled by default |
| Public contact | `PUBLIC_PHONE`, `PUBLIC_EMAIL`, `PUBLIC_ADDRESS`, `PUBLIC_WHATSAPP` | Used in outbound emails |
| Media | `MEDIA_ROOT`, `MEDIA_URL_PREFIXES`, `MEDIA_ALLOWED_HOSTS` | Empty allowlist rejects external photo URLs |
| Workflow | `INQUIRY_TRACK_CONTACT_ON_TRANSITION` | Records first contact when an inquiry leaves `NEW` |

**Where to change what**

- **Infrastructure and secrets** (DB, SMTP credentials, signing key) → `.env`
- **Business settings** (company details, costing defaults, notification addresses) → `/admin/settings`
  (superuser only), stored in the `app_settings` table and cached for 60 seconds

The settings registry in [`app/modules/settings/constants.py`](app/modules/settings/constants.py)
is the single source of truth for setting keys, categories, defaults, validators, and secret flags.

---

## Common commands

### With Make

```bash
make help                         # list every target
make run                          # dev server with autoreload
make migrate                      # alembic upgrade head
make revision message="add x"     # autogenerate a migration
make seed                         # all seed scripts
make superuser                    # interactive superuser creation
make test                         # full test suite
make check                        # validate .env + byte-compile
```

| Target | What it does |
|---|---|
| `make install` | Create `venv/` and install `requirements.txt` |
| `make run` | `uvicorn app.main:app --reload` on `127.0.0.1:8000` |
| `make migrate` | Apply pending migrations |
| `make revision message="..."` | Autogenerate a revision from model changes |
| `make downgrade` | Roll back the latest migration |
| `make seed` / `make seed-settings` | Run all seeds / settings only |
| `make superuser` | Create a superuser |
| `make db-create` / `make test-db` | Create the development / test database |
| `make wait-db` | Wait for PostgreSQL to accept connections |
| `make migrate-check` | Build the full migration chain in a throwaway schema and run `alembic check` |
| `make migrate-sql` | Print offline SQL for every pending migration |
| `make test` / `test-unit` / `test-integration` / `test-cov` | Test suites |
| `make check` | Validate configuration and compile all Python |
| `make docker-env` | Generate `.env.docker` with real secrets |
| `make docker-config` / `docker-build` / `docker-up` / `docker-down` | Compose helpers |
| `make docker-logs` / `docker-ps` | Follow logs / show service status |
| `make docker-migrate` / `docker-seed` / `docker-superuser` | Run maintenance inside the app container |
| `make docker-shell` | Open a shell in the app container |
| `make clean` | Remove Python and test caches |

Override variables when needed:

```bash
make run HOST=0.0.0.0 PORT=8080
make revision message="add invoice due date"
make test-db TEST_DB_NAME=NOCTRADB_test
```

### Without Make

```bash
python -m scripts.seed_all
python -m scripts.seed_settings
python -m scripts.create_superuser
python -m scripts.wait_for_db
python -m pytest tests/ -v
python -m compileall -q app scripts tests
```

---

## Seeding

`python -m scripts.seed_all` runs, in order:

1. **Permissions and roles** — must come first; `create_superuser` needs the `SUPERUSER` role
2. **Application settings** — validates every default against the settings registry
3. **Chart of accounts** — finance account structure
4. **Vehicle catalog** — brands and models
5. **Material catalog** — starter inventory items
6. **Employees** — workshop staff records
7. **Pricing rules** — base pricing tiers

Every seed script is idempotent. Existing operator values are preserved; only missing
rows are inserted. `seed_settings` refuses to run if the seed defaults and the settings
registry drift apart.

---

## Database migrations

```bash
python -m alembic upgrade head
python -m alembic current
python -m alembic history --verbose
python -m alembic revision --autogenerate -m "add due date to invoices"
python -m alembic downgrade -1
```

Notes:

- The database URL comes from `.env`; it is not stored in `alembic.ini`.
- `alembic/env.py` imports `app.core.models_registry`, so every model must stay registered
  there for autogenerate to see it.
- Empty autogenerate revisions are discarded automatically.
- Review autogenerated migrations before applying them.
- Migrations must be idempotent where they touch indexes or columns created by earlier
  revisions; the chain is validated in an isolated schema before release.

Full migration workflow, overrides (`ALEMBIC_DATABASE_URL`, `ALEMBIC_SCHEMA`), and
contributor rules live in [`alembic/README.md`](alembic/README.md).

Before deploying, prove that the migration chain is healthy on a scratch schema:

```bash
make migrate-check
```

It creates a temporary schema in `<POSTGRES_DB>_test`, upgrades it to `head`, runs
`alembic check` to detect model drift, then drops the schema again.

---

## Docker deployment

The repository ships a production-shaped stack: a non-root application image, PostgreSQL 16,
and nginx as the reverse proxy (gzip, cache headers, forwarded client IPs, health probes).

```text
browser ──▶ nginx :8080 ──▶ app :8000 (uvicorn) ──▶ db :5432 (PostgreSQL)
```

Only nginx publishes a host port. The app and database stay on internal Docker networks.

### Quick start

1. **Generate the environment file** — this copies `.env.docker.example` to `.env.docker`
   and replaces `APP_SECRET_KEY` and `POSTGRES_PASSWORD` with strong random values:

   ```bash
   make docker-env
   ```

   Edit `.env.docker` afterwards to set `APP_BASE_URL`, SMTP credentials, and any
   site-specific values. Never commit it.

2. **Start the stack**:

   ```bash
   make docker-up
   ```

   The app container waits for PostgreSQL, applies `alembic upgrade head`, and then starts
   uvicorn. On first boot only, seed reference data and create the admin user:

   ```bash
   make docker-seed
   make docker-superuser
   ```

3. **Open the site** at `http://localhost:8080` (change `HTTP_PORT` in `.env.docker` to use
   another port). Admin login is at `/admin/login`.

### Day-to-day commands

| Command | Purpose |
|---|---|
| `make docker-ps` | Container status and health |
| `make docker-logs` | Follow logs from all services |
| `make docker-migrate` | Apply migrations in the running app container |
| `make docker-seed` | Seed reference data |
| `make docker-superuser` | Create a superuser |
| `make docker-shell` | Shell inside the app container |
| `make docker-down` | Stop the stack (volumes are preserved) |

Useful environment switches in `.env.docker`:

- `RUN_MIGRATIONS` — run `alembic upgrade head` on container start (default `1`)
- `RUN_SEED` — seed once on first boot, then set back to `0`; create the admin with
  `make docker-superuser` (interactive)
- `WEB_CONCURRENCY` — keep at `1`; the rate limiter, email queue, and scheduler are
  in-process
- `TRUST_PROXY_HEADERS` — keep `true` behind nginx; nginx overwrites `X-Forwarded-For`
  with the real client address

### Data and backups

- `db_data` volume — PostgreSQL data directory
- `media_data` volume — uploaded inquiry photos (`/app/media`)

Back up the database with
`docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup.sql`
and archive the media volume alongside it.

### TLS

The default nginx config is HTTP-only. For production, follow
[`deploy/nginx/examples/noctra-tls.conf`](deploy/nginx/examples/noctra-tls.conf): mount
certificates, enable the 443 server, redirect 80 → 443, and set `APP_ENV=production`,
`SESSION_COOKIE_SECURE=true`, and `APP_BASE_URL=https://…` in `.env.docker`. HSTS is emitted
by the application in production; do not duplicate it in nginx.

### Notes

- The image runs as UID/GID `10001` with `no-new-privileges` and all capabilities dropped.
- Health checks use `/healthz`; nginx does not start until the app is healthy.
- `docker compose config`, image builds, and `nginx -t` were not executable in the
  development environment used to author these files (no Docker or nginx installed); the
  Compose file was validated by YAML parsing and the migration flow was verified locally.

---

## Tests

Tests need a live PostgreSQL database named `<POSTGRES_DB>_test` (default `NOCTRADB_test`).

```bash
make test-db          # create it once
make test             # all tests
make test-unit
make test-integration
make test-cov
```

The test session **drops and recreates every table** in the test database. Never point the
tests at a database containing real data.

---

## Routes

| Area | Path | Notes |
|---|---|---|
| Public | `/`, `/about`, `/services`, `/contact` | Inquiry form and post-submit success page |
| Admin | `/admin/login`, `/admin/*` | Session + CSRF protected; RBAC per page |
| API | `/api/v1/*` | JSON API with JWT auth |
| Health | `/healthz`, `/readyz` | For container/orchestrator probes |
| Media | `/media/*` | Uploaded inquiry photos |

---

## Architecture

NOCTRA is a **modular monolith** — one deployable, internally split into domain modules.
Each module follows the same shape: `models.py`, `schemas.py`, `repository.py`, `service.py`,
`api.py`, and `constants.py`. The web layer lives in `app/web` and renders Jinja2 templates
from `app/templates`.

Key behaviours:

- **Request pipeline:** TrustedHost → template context → request ID → rate limit → CSRF
  token → CSRF check → GZip → application.
- **One DB session per request**, committed by middleware before the response is sent so
  commit failures can still surface to the client.
- **RBAC** — permissions are checked in services and routes; roles are seeded and editable.
- **Audit log** — sensitive actions record actor, action, entity, and before/after data.
- **Email queue** — an in-process async queue retries SMTP delivery and logs every attempt.
- **Settings cache** — a 60-second TTL with invalidation on save.

---

## Production checklist

- [ ] Set `APP_ENV=production` and `APP_DEBUG=false` (the app refuses to start otherwise)
- [ ] Generate fresh `APP_SECRET_KEY` and `POSTGRES_PASSWORD` — never reuse development values
- [ ] Set `SESSION_COOKIE_SECURE=true` and serve over HTTPS
- [ ] Set `APP_BASE_URL` to the real public URL (used in emails and links)
- [ ] Restrict `CORS_ORIGINS` and `TRUSTED_HOSTS` to real hosts
- [ ] Enable `TRUST_PROXY_HEADERS` only behind a proxy that strips client-supplied values
- [ ] Configure real SMTP credentials and set `EMAIL_ENABLED=true`; send a test inquiry
- [ ] Run `alembic upgrade head` and back up the database first
- [ ] Persist `media/` (uploaded photos); it is local disk storage
- [ ] Run a single worker, or replace the in-process rate limiter and email queue first
- [ ] Keep `/api/docs` disabled in production — the app does this automatically
- [ ] Run `make migrate-check` against a test database before `alembic upgrade head`
- [ ] Put nginx (or another proxy) in front of the app and enable TLS — see
      [`deploy/nginx/examples/noctra-tls.conf`](deploy/nginx/examples/noctra-tls.conf)
- [ ] Persist and back up the `db_data` and `media_data` Docker volumes

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `APP_SECRET_KEY` rejected (too short or weak) | Replace the `.env.example` placeholder with a 32+ character random value |
| `POSTGRES_PASSWORD is too weak` | Replace the placeholder; the validator rejects common passwords |
| `SESSION_COOKIE_SECURE must be True in production` | Set it to `true` when `APP_ENV=production` |
| `connection refused` on startup | PostgreSQL is not running; check `POSTGRES_*`, then run `make wait-db` |
| `Invalid host header` | Add the hostname to `TRUSTED_HOSTS` |
| Everyone is logged out after a restart | `APP_SECRET_KEY` changed; existing JWTs are invalid |
| Tests fail connecting to DB | Create the test database with `make test-db` |
| Emails are not delivered | `EMAIL_ENABLED=false` by default; check `/admin/email-logs` |
| `ZoneInfoNotFoundError` on Windows | Install dependencies again — `tzdata` is included |
| `seed_settings` reports registry drift | Add the key to both `KNOWN_SETTINGS` and `DEFAULTS` |
| Autogenerate produces an empty migration | Ensure the model is registered in `app/core/models_registry.py` |

---

## Current limitations

- The SMTP settings editable in `/admin/settings` are stored for future use; email delivery
  currently reads the `SMTP_*` / `EMAIL_*` values from `.env`.
- Public contact details are still hardcoded in the public templates; the `PUBLIC_*`
  settings are used by outbound emails.
- Rate limiting and the email queue are in-process — they assume a single application worker.

---

## License

Internal project. All rights reserved.
