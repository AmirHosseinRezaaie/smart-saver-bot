# Architecture Decision Records — Phases 1 & 2

Each record follows: Context → Decision → Reason → Alternatives → Consequences.

## ADR-001: Why Modular Monolith?

**Context.** The project document (chapter 6, "System Architecture") specifies a
layered / service-oriented architecture inside a single Modular Monolith, explicitly
rejecting microservices at this stage.

**Decision.** Build one deployable application, internally divided into
independently-bounded modules (`app/api`, `app/bot`, `app/services`, `app/repositories`,
`app/optimizers`, `app/scrapers`, `app/database`, etc.), each with a clear interface.

**Reason.** Per the document: current expected user volume and operational complexity do
not justify the overhead of running and coordinating multiple independent services.
Module boundaries are still designed as if they *could* become services later (each
module = one package with an explicit interface), so the option isn't foreclosed.

**Alternatives considered.** Microservices from day one — rejected by the document as
premature given current scale. A single unstructured script/app — rejected because it
would not support the planned 15-phase growth (Phase 2 onward add real business logic
into these same boundaries).

**Consequences.** Faster Phase 1–2 delivery and simpler local development/deployment.
Splitting a module into its own service later requires extracting it behind a network
boundary, but the internal interface discipline established now makes that a bounded
task rather than a rewrite.

---

## ADR-002: Why Poetry?

**Context.** The project document (Phase 1 tooling table) lists Poetry as the
recommended dependency manager, with `pip + requirements.txt` as the named alternative.

**Decision.** Use Poetry for dependency management, virtual environment handling, and
packaging.

**Reason.** Per the document: Poetry provides version locking (`poetry.lock`) and an
integrated virtual environment, reducing "works on my machine" drift as the dependency
set grows across 15 phases.

**Alternatives considered.** `pip` + `requirements.txt` (the document's own named
alternative) — workable, but pushes lock-file discipline and virtualenv management onto
separate tools/conventions instead of one. `pip-tools` — similar trade-off, no built-in
packaging story. Neither offered a technical reason strong enough to override the
document's stated preference (per instruction: don't deviate from the document without a
serious technical problem).

**Consequences.** Contributors need Poetry installed locally. `pyproject.toml` is the
single source of truth for metadata and dependencies (no separate `setup.py` or
`requirements.txt`). CI installs Poetry via `pipx` before running any checks.

---

## ADR-003: Why Ruff + Black + MyPy?

**Context.** The project document's Phase 1 tooling table names exactly these three
tools, with Flake8 and Pyright listed as alternatives.

**Decision.** Use Ruff for linting and import sorting, Black for formatting, and MyPy
(in `strict` mode for `app/`) for static type checking. MyPy runs in CI on every push,
but is **not** included in the pre-commit hooks.

**Reason.** Per the document: Ruff is markedly faster than Flake8 for equivalent
coverage; Black removes style debate from code review; MyPy catches runtime type errors
early, which the document flags as particularly valuable for the project's
price/budget-sensitive logic (introduced in later phases). MyPy is excluded from
pre-commit specifically because whole-project type checking is slow enough to degrade
the commit-time experience — CI still enforces it on every PR, so nothing merges
unchecked.

**Alternatives considered.** Flake8 (slower, no built-in import sorting) and Pyright
(the document's named MyPy alternative; not chosen because MyPy is the document's primary
pick and no technical blocker justifies deviating).

**Consequences.** `pyproject.toml` centralizes all three tools' configuration. Strict
MyPy on an otherwise-empty `app/` package is intentionally trivial to pass today; it will
start doing real work as Phase 2+ adds typed business logic.

---

## ADR-004: Why Environment-based Configuration (and no Pydantic yet)?

**Context.** The project document (chapters 11 and Phase 1 "Implementation") requires
all configuration — and especially all secrets — to be read exclusively from
environment variables, with zero hardcoded values, and calls out Pydantic-based
validation specifically in the context of the future FastAPI layer (Phase 2, "Backend
Core").

**Decision.** `app/core/config.py` reads `ENVIRONMENT`, `BALE_BOT_TOKEN`,
`DATABASE_URL`, and `REDIS_URL` from `os.environ` into an immutable stdlib
`dataclass`, with no third-party dependency.

**Reason.** Phase 1 has no HTTP request/response boundary yet — that's exactly where
the document introduces Pydantic (as part of FastAPI input validation in Phase 2).
Adding Pydantic now would be an unnecessary dependency for a module with no schema to
validate, which conflicts with this phase's explicit "don't add dependencies Phase 1
doesn't need" rule. `ENVIRONMENT` is validated eagerly (raises `ConfigError` on an
unrecognized value) because it already affects behavior (`Settings.is_debug`); the other
three fields are read as optional in Phase 1 because no code path consumes them yet —
they'll gain real validation when the layers that need them (bot, database) are built.

**Alternatives considered.** Pydantic `BaseSettings` now — rejected as premature per the
document's own Phase 2 placement of Pydantic. Hardcoded defaults for convenience —
rejected outright; the document treats this as a hard security requirement, not a
preference.

**Consequences.** Zero runtime dependencies in Phase 1. `Settings` will likely be
re-expressed as (or wrapped by) a Pydantic settings model once FastAPI lands in Phase 2;
this is a planned, not accidental, migration.

---

## ADR-005: Why Phase 1 does not implement business logic

**Context.** The project document's Phase 1 section and its own "risks" table
explicitly name premature architectural complexity (over-engineering) as the key risk
for this phase, with the mitigation "skeleton only, no unnecessary code before Phase 2's
real functionality exists."

**Decision.** Phase 1 creates only empty (or near-empty) packages for every future
module (`app/optimizers`, `app/scrapers`, `app/services`, `app/repositories`,
`app/models`, `app/schemas`, `app/database`, `app/bot`, `app/api`), plus a configuration
module, an entry point, and a smoke test. No search, basket optimization, OKALA
integration, Bale bot handling, database migrations, background jobs, or authentication
is implemented.

**Reason.** Building any of that now would mean guessing at interfaces the later phases
(which the document specifies in detail — e.g. chapter 8 for basket optimization,
chapter 9 for the Bale bot design) haven't been reached yet in the plan, risking rework
and violating the document's explicit Phase 1 scope and acceptance criteria (structure +
tooling + a passing smoke test — nothing more).

**Alternatives considered.** Pre-building partial implementations "to save time later" —
rejected: this is precisely the over-engineering risk the document itself calls out for
this phase.

**Consequences.** Phase 1's `pytest` suite only proves import/config/construction, not
correctness of any real feature — that's expected and by design. Phase 2 ("Backend
Core") is the next unit of work, per the document's own phase ordering.

---

## ADR-006: Why migrate to Pydantic Settings now, and why Backend Core stays bot-independent

**Context.** The project document places Pydantic explicitly in Phase 2 ("Backend
Core"), alongside FastAPI, and states that the Backend Core should be built independent
of the bot's business logic so a general-purpose API (e.g. for a future mobile app) can
be added later without touching business logic.

**Decision.** `app/core/config.py` is rewritten from the Phase 1 stdlib `dataclass` (see
ADR-004) to a `pydantic_settings.BaseSettings` subclass. It remains the single
configuration source of truth: nothing else in the codebase reads `os.environ` directly,
including `alembic/env.py` (see ADR-010). `app/main.py`, `app/api`, and `app/core` contain
no reference to Bale, OKALA, or any business concept — only FastAPI composition,
configuration, exception handling, and infrastructure wiring.

**Reason.** Phase 1 deferred Pydantic specifically because there was no request/response
boundary yet to validate (ADR-004). That boundary now exists (`/health`'s response model,
and `RequestValidationError` handling for future endpoints), so the originally-planned
migration happens now. Keeping `app/api`/`app/core` free of bot-specific code is what lets
Phase 5's Bale bot and any hypothetical future consumer (mobile app, admin panel) sit on
top of the same Backend Core without a rewrite.

**Alternatives considered.** Keeping the Phase 1 dataclass and hand-rolling validation
directly in FastAPI dependencies — rejected: the document explicitly assigns Pydantic to
this role, and hand-rolling it would duplicate work Pydantic already does well.

**Consequences.** `Settings` is now a Pydantic model (still effectively immutable —
`frozen=True` in `model_config`), validated eagerly at `Settings()` construction time
rather than lazily per-field. A production deployment with `DEBUG=true` now fails at
startup (`ValidationError`) instead of silently running with verbose errors exposed — see
ADR's "Secure Configuration" requirement in the project document, chapter 11.

---

## ADR-007: Why a single lazily-built async SQLAlchemy engine

**Context.** The project document requires an async PostgreSQL connection via SQLAlchemy,
a managed connection pool, and warns explicitly against a misconfigured pool degrading
performance under load (Phase 2 risk table).

**Decision.** `app/database/session.py` builds exactly one process-wide `AsyncEngine` and
one `async_sessionmaker`, both created lazily on first use (not at module import time) and
cached at module level. `get_db_session()` is the one FastAPI dependency every future
endpoint/repository uses to get a request-scoped `AsyncSession`; `session_scope()`
provides the same pattern for non-request code paths (background jobs, scripts). Pool
sizing (`pool_size`, `max_overflow`, `pool_timeout`) is configurable via `Settings`
instead of hardcoded, with `pool_pre_ping=True` always on to avoid handing out stale
connections.

**Reason.** A single shared engine is what actually gives you connection pooling — engines
created per-request or per-module would each open their own pool, defeating the point and
risking exhausting PostgreSQL's `max_connections`. Building it lazily (rather than at
import time) keeps `import app.main` side-effect-free, which matters for tests (import
must never require a live database) and for the reasoning in ADR-004/ADR-005 about what
each phase's code is allowed to assume is available. Configurable pool settings (rather
than hardcoded ones) let the Phase 2 risk (misconfigured pool under load) be tuned without
a code change.

**Alternatives considered.** A dependency-injection framework managing the engine's
lifecycle — rejected as over-engineering for a single-engine, single-process application
(project document's own Phase 2 "avoid over-engineering" guidance, mirrored in this
project's general anti-over-engineering rule). Opening a new engine per request — rejected
outright; this is the exact anti-pattern connection pooling exists to prevent.

**Consequences.** `dispose_engine()` (called from `app/main.py`'s `lifespan` shutdown
handler) is required to release pooled connections cleanly on process exit; forgetting to
call it would leak connections across restarts in an environment that reuses the process
(e.g. some test runners). `reset_engine_for_tests()` exists specifically so integration
tests can point `DATABASE_URL` at a different target per test without a stale engine from
a previous test silently reused.

---

## ADR-008: Why a single lazily-built async Redis client

**Context.** The project document requires a Redis connection for caching, with timeout
handling and the same "no premature complexity" guidance as PostgreSQL.

**Decision.** `app/database/redis.py` mirrors ADR-007's pattern exactly: one process-wide
`redis.asyncio.Redis` client, built lazily from `Settings.redis_url`, with
`socket_timeout`/`socket_connect_timeout` both bound to `Settings.redis_timeout`.

**Reason.** Consistency with the PostgreSQL pattern (ADR-007) keeps the infrastructure
layer predictable, and `redis.asyncio.Redis` already pools its own connections
internally, so a single shared client is both correct and sufficient — there is no
Phase-2-relevant reason to add anything more (e.g. a custom pool wrapper, a caching
abstraction layer) ahead of Phase 8 ("Database تکمیلی، Cache و Background Jobs"), where
actual caching business logic is scheduled.

**Alternatives considered.** Building a caching abstraction (get/set/invalidate helpers)
now — rejected as out of Phase 2's explicit scope (the project document places caching
*business logic* in Phase 8); this phase provides only the connection itself.

**Consequences.** `close_redis()` is called from `app/main.py`'s shutdown hook,
mirroring `dispose_engine()`. Cache helpers (get/set/invalidate wrappers, TTL policy,
key-naming conventions) are Phase 8's job, not Phase 2's.

---

## ADR-009: Why no ORM models are added in Phase 2

**Context.** The project document explicitly restricts Phase 2 to backend
*infrastructure* and defers all business-specific database models to the phases that
actually need them, echoing Phase 1's own anti-over-engineering rationale (ADR-005).

**Decision.** `app/database/base.py` defines only the shared `Base(DeclarativeBase)` that
future models will inherit from. No `User`, `Product`, `Store`, `Price`, `Discount`, or
`Basket` model is created in this phase. The one Alembic migration this phase ships
(`b9a2079e6af1`) is intentionally a no-op — it proves the migration pipeline runs
end-to-end against a real PostgreSQL database without committing to any schema ahead of
the phase (Phase 3+) that actually needs one.

**Reason.** Guessing at these models now — before Phase 4/7's detailed data-design
chapter is reached in implementation order — risks the same rework ADR-005 flags for
Phase 1's business logic. The project document is explicit that Phase 2's own deliverable
is "an executable backend, ready to have business logic added," not the business logic's
data model itself.

**Alternatives considered.** Pre-building a `User`/`Product` skeleton "to save time later"
— rejected for the same reason ADR-005 rejected it for Phase 1: this is precisely the
over-engineering risk the document calls out.

**Consequences.** `alembic revision --autogenerate` will currently generate an empty
diff (correctly — there is nothing to diff against yet). The first migration with real
`op.*` calls will come from Phase 3 onward, once real models exist.

---

## ADR-010: Why Alembic reads `DATABASE_URL` from `Settings`, not `alembic.ini`

**Context.** The project document requires Alembic to be wired to the database without
hardcoding a connection string, and this project's own configuration rule (chapter 11,
mirrored in ADR-006) forbids two parallel configuration systems.

**Decision.** `alembic.ini` leaves `sqlalchemy.url` unset (commented out, with an
explanatory note). `alembic/env.py` imports `app.core.config.get_settings()` and calls
`config.set_main_option("sqlalchemy.url", settings.database_url)` before running
migrations either online or offline.

**Reason.** This makes `Settings` (and therefore `DATABASE_URL` from the environment) the
single source of truth for the connection string used by *both* the application and
Alembic — exactly the "no parallel config systems" rule ADR-006 states for the rest of
the project. It also means Alembic never has a real credential committed anywhere in the
repository, satisfying the project document's chapter 11 Secret Management requirement.

**Alternatives considered.** Setting `sqlalchemy.url` directly in `alembic.ini` (even via
an `%(ENV_VAR)s`-style interpolation) — rejected because Alembic's own interpolation
syntax is a second, parallel way to reference the same environment variable, instead of
funneling through the one `Settings` object everything else uses.

**Consequences.** Running any `alembic` command requires the same environment
`DATABASE_URL` the application itself needs — there is no separate "migration-only"
database configuration to keep in sync.

---

## ADR-011: Why `docker-compose.yml` exists, and why it is not a deployment artifact

**Context.** The project document's Phase 2 testing section calls for integration tests
against a temporary PostgreSQL/Redis, "e.g. via Docker," while explicitly scoping
production deployment to Phase 12 ("Docker، CI/CD و Deployment").

**Decision.** `docker-compose.yml` provides local `postgres:16` and `redis:7` containers
for development and for running the integration test suite, matching the credentials in
`.env.example`. It has no application container, no production-oriented settings
(resource limits, restart policies, secrets management), and is not referenced by the CI
pipeline, which uses GitHub Actions' own `services:` blocks instead (see
`.github/workflows/ci.yml`).

**Reason.** The document calls for exactly this — a convenient way to get throwaway
PostgreSQL/Redis instances for local development and testing — without pulling forward
any of Phase 12's actual deployment concerns (application containerization, orchestration,
CI/CD to a live environment).

**Alternatives considered.** No Docker Compose file at all, relying on a locally-installed
PostgreSQL/Redis — rejected as worse developer experience and less reproducible than the
project document's own suggested approach; kept as the documented option, not the only
one (a local install works identically as long as the same connection details are used).

**Consequences.** `docker compose up -d` becomes the recommended (not mandatory) way to
get a working local environment. Production container definitions, if any, are Phase 12's
responsibility and do not belong in this file.

---

## Deviations from literal document wording (flagged per instructions)

These are small, non-architectural naming choices where the document's own text
contains two different labels for the same artifact; both are consistent with a
standard Poetry/`.gitignore` setup, and this repository follows the document's Git
chapter (12.4) as the more specific, executable spec:

- **Environment example filename.** Chapter 12.4's `.gitignore` sample uses the
  pattern `!.env.example`, implying the file is named `.env.example`. This repository
  uses that name (a Phase 1 task list elsewhere refers to it as `.example.env`). This
  is a naming choice only — content and purpose (placeholder values, never committed
  with real secrets) are identical either way.

- **`DATABASE_URL` driver qualifier.** The project document's own example URL
  (`postgresql://user:********@localhost:5432/shopping_bot`) uses the plain
  `postgresql://` scheme. This repository's `.env.example` uses
  `postgresql+asyncpg://...` instead. This is required, not optional: SQLAlchemy
  selects a DBAPI driver from the URL scheme, and the plain `postgresql://` scheme
  resolves to the synchronous `psycopg2` driver, which cannot be used with
  `create_async_engine` (Phase 2's explicit "no blocking database calls" requirement).
  `+asyncpg` is the async driver Phase 2 installs and uses throughout
  `app/database/session.py`.

## ADR-012: Why the OKALA adapter targets a generic `schema.org/Product` contract

**Context.** Phase 3 (project document, chapter 10.1) requires resolving how OKALA
data is actually obtained before building anything on top of it, and explicitly
forbids inventing endpoints or bypassing robots/ToS restrictions. This environment's
own fetch tool refused `https://www.okala.com/` on robots-exclusion grounds, so
OKALA's real markup could not be sampled at all — see `docs/okala-research.md` for
the full, dated investigation.

**Decision.** `app/scrapers/okala_provider.py` implements `OkalaProviderInterface`
against the standard, publicly documented `schema.org/Product` JSON-LD structure —
the exact fallback the project document itself names when no official API exists —
rather than against any OKALA-specific endpoint or HTML shape. `Settings.okala_provider_base_url`
has no default, so the adapter cannot reach any host, OKALA included, until an
operator configures one after completing the verification `docs/okala-research.md`
lists as outstanding.

**Consequence.** The adapter, its bounded-retry HTTP client, and its raw-response
snapshotting are fully unit-tested against fixed fixtures (`tests/unit/test_okala_*.py`)
and ship in this phase, but the Phase 3 acceptance criterion of fetching one real
OKALA product cannot be marked verified yet. `httpx` moves from a test-only to a
runtime dependency accordingly (it was already used for `TestClient`/integration
tests; the provider adapter is its first production use).
