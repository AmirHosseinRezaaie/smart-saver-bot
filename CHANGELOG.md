# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Initial repository structure (`app/`, `tests/`, `scripts/`, `docs/`,
  `.github/workflows/`) reflecting the layered / modular-monolith architecture.
- Environment-based configuration (`app/core/config.py`).
- Development tooling: Poetry, Ruff, Black, MyPy.
- Pre-commit hooks (Ruff, Black, and basic hygiene checks).
- Initial GitHub Actions CI pipeline (lint, format check, type check, test).
- Smoke test proving the application imports, configures, and constructs without error.
- Project documentation: README, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, and
  architecture decision records.
