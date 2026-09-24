# Contributing to Smart Saver Bot

## Branching

- Branch from `develop` (never directly from `main`).
- Name branches by type: `feature/<short-description>`, `fix/<short-description>`,
  `hotfix/<short-description>`.
- Example: `feature/project-bootstrap`.

## Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add basket optimization endpoint
fix: handle unavailable products
chore: configure ruff, black, mypy
docs: update setup instructions
test: add smoke test
refactor: extract economic score calculator
```

Keep commits small and atomic — one logical change per commit.

## Pull Requests

- Open PRs against `develop` (or `main`, only for `hotfix/*` branches).
- Require at least one reviewer approval before merging.
- CI (lint, type-check, test) must pass before merge.
- Describe *what* changed and *why* in the PR description; link the relevant phase or
  issue if applicable.

## Tests

- Add or update tests for any behavior change.
- Tests must be deterministic and must not depend on the network, OKALA, Bale, a real
  PostgreSQL instance, or a real Redis instance.
- Run locally before opening a PR:

  ```bash
  poetry run pytest
  ```

## Lint & Formatting

Run and fix locally before committing:

```bash
poetry run ruff check . --fix
poetry run black .
poetry run mypy app/
```

Installing the pre-commit hooks catches most of this automatically:

```bash
poetry run pre-commit install
```
