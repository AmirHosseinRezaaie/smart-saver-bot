# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- OKALA data source investigation report (`docs/okala-research.md`), distinguishing
  verified findings from open questions per the project document's Phase 3 requirement.
- `OkalaProviderInterface` (`app/scrapers/interfaces.py`) and a concrete
  `OkalaProvider` adapter built on the generic `schema.org/Product` structured-data
  contract, with bounded timeout/retry (`app/scrapers/http_client.py`), raw-response
  snapshotting for debugging (`app/scrapers/snapshot.py`), and raw/internal catalog
  schemas (`app/schemas/okala.py`, `app/schemas/catalog.py`).
- OKALA provider configuration in `Settings` (base URL, timeout, retry, snapshotting)
  and matching entries in `.env.example`.
- `Provider*` exception hierarchy in `app/core/exceptions.py` for provider failures.
- `httpx` promoted to a runtime dependency (was test-only) for the provider adapter.

- Initial repository structure (`app/`, `tests/`, `scripts/`, `docs/`,
  `.github/workflows/`) reflecting the layered / modular-monolith architecture.
- Environment-based configuration (`app/core/config.py`).
- Development tooling: Poetry, Ruff, Black, MyPy.
- Pre-commit hooks (Ruff, Black, and basic hygiene checks).
- Initial GitHub Actions CI pipeline (lint, format check, type check, test).
- Smoke test proving the application imports, configures, and constructs without error.
- Project documentation: README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, and
  architecture decision records.
