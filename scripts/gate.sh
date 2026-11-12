#!/usr/bin/env bash
# The gate CI runs, run here first.
#
#     scripts/gate.sh
#
# Every step below is a step of the `lint-and-test` job in `.github/workflows/ci.yml`,
# in the same order and with the same command — `tests/scripts/test_gate.py` fails when
# the two drift apart. One deliberate difference: CI installs with `uv sync --locked`,
# which here would rewrite the developer's environment, so the gate asks the only
# question that flag answers — is uv.lock current? — with `uv lock --locked`, which
# changes nothing.
#
# The verdict is the exit code and the last line, never the output in between:
# "630 passed" is not the coverage floor that refused the run two lines further down.
# Nothing here greps output.
set -uo pipefail

# The glob of the last step is expanded by this shell, so the gate stands in the
# repository root rather than wherever it was called from: an empty glob would leave
# nothing to check, and the step would pass.
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root" || exit 2

if [ "$#" -gt 0 ]; then
  printf 'usage: %s   (no arguments: it runs every check CI runs)\n' "${0##*/}" >&2
  exit 2
fi

failed=()

# Colour for a terminal only: the gate is also run into a log file, read later.
bold='' green='' red='' reset=''
if [ -t 1 ]; then
  bold=$'\033[1m' green=$'\033[32m' red=$'\033[31m' reset=$'\033[0m'
fi

# A failed step does not stop the gate: the next one still runs, and the summary
# names every step that failed.
step() {
  local name="$1"
  shift
  printf '\n%s── %s%s\n' "$bold" "$name" "$reset"
  if "$@"; then
    printf '%sok%s — %s\n' "$green" "$reset" "$name"
  else
    printf '%sFAILED%s — %s\n' "$red" "$reset" "$name"
    failed+=("$name")
  fi
}

step "lockfile"     uv lock --locked
step "ruff check"   uv run ruff check
step "ruff format"  uv run ruff format --check
step "ty"           uv run ty check evlampiy
step "pytest"       uv run pytest
step "shellcheck"   shellcheck scripts/*.sh

printf '\n'
if [ ${#failed[@]} -eq 0 ]; then
  printf '%sall gates passed%s\n' "$green" "$reset"
  exit 0
fi
printf '%sfailed:%s\n' "$red" "$reset"
printf '  %s\n' "${failed[@]}"
exit 1
