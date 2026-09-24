# Architecture Decision Records — Phase 1

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
