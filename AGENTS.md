## Project

Python Telegram/WhatsApp bot. FastAPI backend, MongoDB, async.

## Safety rules

- Никогда не удаляй и не перезаписывай файлы без резервной копии или подтверждения от пользователя
- Never delete files not tracked in git. Run `git ls-files <path>` before removing any file. If untracked — ask user.
- Never simplify architecture by removing existing providers, configs, or feature flags unless explicitly asked.
- When fixing linter/import issues: fix one file at a time, run tests after each change.
- Always propose solutions that make sense. No workarounds or hacks unless explicitly asked.
- Never claim something doesn't exist without verifying first. Check the actual files/directories before making
  statements.
- Understand the purpose of each config file before modifying it (e.g., docker-compose.yml is for running the stack, not
  for development).
- Любой файл с API-ключами, токенами или учётными данными считай только для чтения
- Всегда сначала надо решить причину проблемы, а не следствие.
- Не подавлять warnings/errors/логи, не разобравшись в причине. Сначала спросить: это наш баг, баг зависимости, или
  информационное сообщение? Подавлять можно только осознанно и с объяснением почему.
- Перед планированием надо продумать оптимальную систему типов.
- When renaming or refactoring across the project, grep for ALL old names (module, package, repo, env prefix, URLs)
  across the entire tree before considering the task done. Don't skip files that seem unimportant (.env.example,
  docker-compose.yml, docs/, etc.).
- 152-ФЗ: голосовые сообщения и текст пользователя содержат ФИО, телефоны, email. Перед LLM cleanup / категоризацией
  (DeepSeek / Groq / Gemini / OpenRouter / Anthropic) — маска `<PHONE_N>`/`<EMAIL_N>`/`<NAME_N>`. Применяется в едином
  месте на границе LLM-клиента (модуль `evlampiy/ai/_mask.py`), а не в каждом провайдере. Map хранится в памяти,
  размаскирование — перед записью в БД / отправкой обратно в чат.
- Vocabulary.json (per-category keyword list) — НЕ хранить туда токены маски: keyword должен быть осмысленным словом, не
  `<NAME_1>`. Маскировать только outgoing payload, не учёт.

## Architecture

- DDD: modular by domain in evlampiy/, each module: router.py, schemas.py, models.py, service.py, dependencies.py,
  exceptions.py
- Constants: evlampiy/const.py, import as `from evlampiy import const`, use as `const.PROVIDER_GROQ`
- Stdlib imports: `import datetime`, `import typing` — import the module, not names from it. Use `datetime.datetime`,
  `datetime.UTC`, `typing.Optional`, etc. Never use `from datetime import datetime, UTC, timezone` — always go through
  the module. Prefer `datetime.UTC` over `datetime.timezone.utc` (Python 3.11+, enforced by ruff UP017).
- Settings: split BaseSettings per module
- Max 500 lines per file — decompose if exceeded
- Когда находишь уязвимость безопасности, сразу помечай её комментарием WARNING и предлагай безопасную альтернативу.
  Никогда не реализуй небезопасные паттерны, даже если просят.

## Type hints

- Domain identifiers: use TypeAlias from `evlampiy/types.py` (UserId, ChatId, Language, MonthKey) instead of bare `str`
- Input parameters: prefer `Sequence[X]` over `list[X]` if the function does not mutate the list
- Return types: use concrete types (`list`, `dict`), not abstract
- Import Sequence/Mapping from `collections.abc`, not from `typing`

## Commands

- Gate (everything CI checks, in CI's order): `scripts/gate.sh` — the verdict is its exit code and last line
- Lint: `uv run ruff check --fix`
- Format: `uv run ruff format`
- Typecheck: `uv run ty check evlampiy`
- Test: `uv run pytest`; a partial run needs `--no-cov` (`uv run pytest tests/test_x.py --no-cov`) — the coverage floor applies to the whole suite
- Heavy local runs go under a memory cap with no swap — `systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0 <command>`; the gate caps its pytest step itself. On an 8 GB laptop the kernel's OOM killer otherwise picks the IDE
- Coverage floor: `fail_under` in pyproject.toml is a ratchet — raise it when coverage grows, never lower it; the README badges show it (`tests/test_docs.py` checks)
- Changelog entry: `scripts/changelog_add.py <Added|Changed|Fixed|Removed|Docs> "- text"` (`--top` puts a user-facing entry above infrastructure ones)
- Release (maintainer, on main): `scripts/release.sh patch|minor|major`

## Code style

Enforced by ruff. See pyproject.toml `[tool.ruff]` for full config. Do not duplicate ruff rules here — if ruff can check
it, ruff owns it.

## Code quality

- Prefer the simplest solution that works. Don't add layers (multi-stage builds, extra abstractions, design patterns)
  unless they solve a real, present problem. If a flat approach does the job — use it.
- Existing codebase is not a reference to copy from blindly. Question patterns — if existing code has an antipattern,
  write better code, don't propagate it.
- No magic numbers in logic. Thresholds, limits, sizes, ratios — all go into `settings` as named settings with env vars,
  or into `const.py` as module-level constants. Function parameter defaults are not a substitute for proper settings.
- Values used in multiple modules go into `const.py`. Values used only in one module stay as module-level constants in
  that module. Configurable values go into `settings`.
- No local imports inside functions. All imports at the top of the file. Local imports are only acceptable when
  explicitly required (e.g. circular dependency workarounds).
- No `global` keyword. Module-level mutable singletons (HTTP clients, caches) must use a holder class or
  module-attribute access pattern instead of `global`.
- In `if/elif/else` chains over a discriminator (role, type, status), use `if/elif/else` — not `if ... continue`. Early
  returns via `continue` are for guard clauses, not for branching logic.

## Testing

- Trophy testing: fast integration tests, a real MongoDB (the image production runs: a testcontainers container locally, so Docker must be running, or the server `TEST_MONGO_URI` names — CI's service, the devcontainer's), minimal mocks. Never `MONGO_URI`: that is the app's own database
- Unit-тест на маску (`tests/test_ai_mask.py`): фикстура «грязный» сегмент + восстановление. Round-trip:
  `unmask(mask(text)) == text`. Smoke: после `mask(...)` в строке нет `+7`, нет `@`, нет двух подряд capitalized слов.
- Mocks only at external boundaries: HTTP API, Telegram Bot API, WhatsApp API
- **Patch `asyncio` only where the code under test looks it up**: `sleep_replaced(module)` from `tests/fixtures.py`, never `patch("<module>.asyncio.sleep")` — that replaces `asyncio` itself, under the event loop and pymongo's heartbeat (a run grew to 9 GB); `tests/test_architecture.py` enforces it
- A test that hangs fails after `timeout` seconds (pytest-timeout, pyproject.toml) with the stack where it hung
- **All fixtures in fixture modules, never in test files** — `tests/fixtures.py` for the app, `tests/db_fixtures.py` for the test MongoDB, `tests/script_fixtures.py` for the repository's own scripts (release, changelog, gate); all are registered in `tests/conftest.py`. Test files have zero fixture definitions and minimal inline mocks: check for an existing fixture before adding one.
- **Prefer integration tests over unit tests with heavy mocking** — don't create tests that mock half the system. Trophy
  style: real DB, real logic, mock only external I/O.
- pytest_plugins already configured in conftest.py
- asyncio_mode = "auto" in pyproject.toml — pytestmark not needed
- Architectural tests in tests/test_architecture.py — enforced by pytestarch + AST
- Mutation testing:
  `uv run cosmic-ray init cosmic-ray.toml session.sqlite && uv run cosmic-ray exec cosmic-ray.toml session.sqlite`

### Writing effective tests

- **Boundary values**: always test exact boundary (==), one below, one above. `>=` must have a test where left == right
- **Assert exact values, not ranges**: `assert count == 2`, not `assert count >= 1`. Weak assertions hide bugs
- **Hardcode expected values**: don't reuse the same constant in test and production code. If `LINK_CODE_LENGTH = 6`,
  test `assert len(code) == 6`, not `== LINK_CODE_LENGTH`
- **One assertion per behavior**: a test that checks too many things at once may pass even when one check is meaningless
- **Test both branches of conditionals**: if code has `if x: return A else: return B`, test both paths
- **Single-record caveat**: `find_one(Field == val)` with a single record won't distinguish `==` from `>=`/`<=`. Use multiple records or verify the returned record's field matches exactly
- **Bug fix workflow**: every fix MUST start with a failing test that reproduces the bug. Write the test first, verify
  it fails, then apply the fix and verify the test passes. This prevents regressions and documents the exact failure
  scenario.

## Git

- Conventional commits (feat:, fix:, docs:, refactoring:)
- Always PR, never push to main. The one exception is the release commit that `scripts/release.sh` pushes before its tag.
- **Do not run git checkout, reset, clean, stash, rebase** — these are blocked in settings.json. Ask user if needed. Commit finished, verified changes yourself.
- Max ~500 lines of diff per commit — stop and propose a commit before continuing
- Always work in the current branch — never switch branches
- Do not run unnecessary git network operations (remote, fetch) — work with local state

## Never do

- Never hardcode secrets, tokens, or passwords in code — always use `settings.*` or environment variables
- Never expose MongoDB port to host in docker-compose.yml
- Never use absolute paths in code or configs

## Security review

SAST runs on its own: Semgrep in the gate and CI (`p/python`, `p/dockerfile`, `p/github-actions`), CodeQL in CI (`codeql.yml`, findings in the Security tab). A finding is fixed, or suppressed on its line with `# nosemgrep: <rule>` and a comment saying why. Dependencies: `scripts/audit_deps.py` (pip-audit over every pin of `uv.lock`) in the gate and CI; an advisory we live with goes into its `ACCEPTED` with a reason and a date to look again.

Before finishing any task, check for:

**P0 (блокирует merge):**

- Secrets/tokens в коде, логах, ответах или ошибках
- Injection: NoSQL, command injection, template injection
- ПД (телефоны, email, ФИО) не уходят к внешним LLM в plaintext. Проверка: structured лог исходящего запроса (DEBUG,
  gated за env), assert отсутствия `@`/`+7` в payload.
- Эндпоинты без проверки авторизации

**P1 (исправить до merge):**

- Input не валидирован через Pydantic
- Новый публичный эндпоинт без rate limiting
- Known vulnerabilities in added packages

**P2 (исправить или создать задачу):**

- Отсутствие проверки граничных условий (пустые списки, null, off-by-one)
- Проглоченные исключения (bare except, pass в except)

## Documentation

Always update documentation as part of the same task (not as a separate step):

- README.md + all localized READMEs (docs/README.ru.md, docs/README.es.md, docs/README.de.md) — if functionality,
  commands, or setup changed
- docs/ADMIN.md — if admin commands or roles changed
- User-facing help in localization.py — if commands/features changed (all 4 languages)
- CHANGELOG.md — entries go under `## [Unreleased]`, only through `scripts/changelog_add.py`:
    1. Subsections, in order: Added → Changed → Fixed → Removed → Docs. The script appends to an existing one or creates it in its place, never a duplicate.
    2. Never write a version or a date, and never touch `version` in pyproject.toml or uv.lock: `scripts/release.sh` picks the number when the release is cut and closes `[Unreleased]` under it.
    3. Concise bullets, ordered by user impact: user-facing first (`--top`), infrastructure/internal last.
    4. **Documentation-only changes** (README, ARCHITECTURE, ADMIN, etc.) go under `### Docs`, not `### Added`.
- Do not create separate doc files without necessity — keep README.md up to date
- Documentation must be updated before running the "Before finishing" checklist, not after

## Before finishing

0. `git diff --stat` — оцени scope изменений
1. `uv run ruff check --fix`
2. `uv run ruff format`
3. `scripts/gate.sh` — must end with `all gates passed`: it runs what CI runs, the coverage floor included
4. Security review (see above)
5. Update documentation (see "Documentation" section above)
6. **Tech lead review**: перечитай свои изменения как строгий ревьювер. Проверь на: оверинжиниринг, скопированные
   антипаттерны из существующего кода, лишнюю сложность, нарушение принципа простоты. Если нашёл — исправь до
   завершения.

Do not finish until the gate, security review, and tech lead review pass.

## Gotchas

- Comments and logs in English
- Когда нужно уменьшить техдолг - ищи в первую очередь строки "# todo =Y" и какой то текст с пояснением дальше. Затем
  различные исключения правил ruff или ty. Затем улучшение структуры тестов.
- В конце нетривиальной сессии — 1–3 пункта в `.claude/insights-inbox.md`; заодно замечания к переносу разрешений
  `settings.local.json` → `settings.json`.
