# CLAUDE.md

## Project

Python Telegram/WhatsApp bot. FastAPI backend, MongoDB, async.

## Safety rules

- Never delete files not tracked in git. Run `git ls-files <path>` before removing any file. If untracked — ask user.
- Never simplify architecture by removing existing providers, configs, or feature flags unless explicitly asked.
- When fixing linter/import issues: fix one file at a time, run tests after each change.
- Always propose solutions that make sense. No workarounds or hacks unless explicitly asked.

## Architecture

- DDD: modular by domain in src/, each module: router.py, schemas.py, models.py, service.py, dependencies.py,
  exceptions.py
- Constants: src/const.py, import as `from src import const`, use as `const.PROVIDER_GROQ`
- Stdlib imports: `import datetime`, `import typing` — import the module, not names from it.
  Use `datetime.datetime`, `datetime.timezone.utc`, `typing.Optional`, etc.
  Never use `from datetime import UTC` — use `datetime.UTC` instead.
- Settings: split BaseSettings per module
- Max 500 lines per file — decompose if exceeded
- FastAPI conventions: see .claude/skills/fastapi.md

## Commands

- Lint: `uv run ruff check --fix`
- Format: `uv run ruff format`
- Test: `uv run pytest`
- Coverage must be >= 85%

## Code style

Enforced by ruff. See pyproject.toml `[tool.ruff]` for full config.
Do not duplicate ruff rules here — if ruff can check it, ruff owns it.

## Testing

- Trophy testing: fast integration tests, real DB (mongomock), minimal mocks
- Mocks only at external boundaries: HTTP API, Telegram Bot API, WhatsApp API
- Fixtures in tests/fixtures.py as @pytest.fixture, accessed via test parameters (NOT via import)
- pytest_plugins already configured in conftest.py
- asyncio_mode = "auto" in pyproject.toml — pytestmark not needed

## Git

- Conventional commits (feat:, fix:, docs:, refactoring:)
- Always PR, never push to main
- **Do not run git commit, checkout, reset, clean, stash, rebase** — these are blocked in settings.json. Ask user if needed.
- Max ~500 lines of diff per commit — stop and propose a commit before continuing
- Always work in the current branch — never switch branches

## Security review

Before finishing any task, check for:

- Secrets/tokens leaking into logs, responses, or error messages
- Injection: NoSQL, command injection, template injection
- Input validation: all user input validated via Pydantic before use
- Authorization: no endpoints accessible without proper auth checks
- Rate limiting: new public endpoints must have rate limits
- Dependencies: no known vulnerabilities in added packages

## Documentation

Always update documentation as part of the same task (not as a separate step):

- README.md + all localized READMEs (docs/README.ru.md, docs/README.es.md, docs/README.de.md) — if functionality, commands, or setup changed
- docs/ADMIN.md — if admin commands or roles changed
- User-facing help in localization.py — if commands/features changed (all 4 languages)
- Do not create separate doc files without necessity — keep README.md up to date
- Documentation must be updated before running the "Before finishing" checklist, not after

## Before finishing

1. `uv run ruff check --fix`
2. `uv run ruff format`
3. `uv run pytest`
4. Verify coverage >= 85%
5. Security review (see above)
6. Update documentation (see "Documentation" section above)

Do not finish until lint, tests, and security review pass.

## Gotchas

- Comments and logs in English
- Frontend: Solid.js
