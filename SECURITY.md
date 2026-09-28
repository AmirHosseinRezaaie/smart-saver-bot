# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Smart Saver Bot, please report it privately
rather than opening a public issue. Open a private security advisory on the repository
(or contact the maintainers directly, if a contact channel is published there) with:

- A description of the vulnerability and its potential impact.
- Steps to reproduce it.
- Any relevant logs or proof-of-concept code (with secrets redacted).

Please allow a reasonable amount of time for the issue to be assessed before any public
disclosure.

## Secret Handling

- No token, password, API key, or database credential is ever committed to source
  control, documentation, or the README.
- All secrets are read exclusively from environment variables at runtime
  (`app/core/config.py`), never hardcoded.
- `.env` and any file containing a real secret is excluded via `.gitignore`; only
  `.env.example`, containing placeholder values, is committed.
- In CI/CD and hosting environments, secrets are stored in the platform's secret manager
  (e.g. GitHub Actions Secrets), not in the repository.
- If a secret is ever accidentally committed, it must be rotated immediately, not just
  removed from the latest commit — Git history retains it otherwise.

## Developer Responsibilities

- Never log a token, password, or other sensitive identifier in full; if a value must be
  logged for debugging, mask all but its last few characters.
- Validate all external and user input before it reaches business logic.
- Use the project's ORM with parameterized queries; never build SQL via string
  concatenation.
- Keep dependencies up to date and review dependency vulnerability alerts
  (e.g. `pip-audit`, GitHub Dependabot) periodically.
- Ensure debug mode and verbose error output are disabled in any production
  configuration (`ENVIRONMENT=production`).
