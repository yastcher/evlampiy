#!/usr/bin/env bash
# The gate CI runs, run here first.
#
#     scripts/gate.sh
#
# Every step below is a step of the `lint-and-test` job in `.github/workflows/ci.yml`,
# in the same order and with the same command — `tests/scripts/test_gate.py` fails when
# the two drift apart. Two deliberate differences: CI installs with `uv sync --locked`,
# which here would rewrite the developer's environment, so the gate asks the only
# question that flag answers — is uv.lock current? — with `uv lock --locked`, which
# changes nothing; and the tests run under a memory cap (below), which a laptop needs
# and a CI runner does not.
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

# The tests run in a scope with a memory limit and no swap: a runaway test then kills the
# run, not the IDE the kernel's OOM killer would pick on an 8 GB laptop — a test run once
# grew to 9 GB, most of it in swap. The suite peaks near 320 MB. Stopping a scope also stops
# every process in it, so an interrupted run leaves no pytest behind. Without a systemd user
# session (the devcontainer, macOS) the tests run as CI runs them, uncapped.
capped=()
if systemd-run --user --scope --quiet true >/dev/null 2>&1; then
  capped=(systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0)
else
  printf 'note: no systemd user session, so pytest runs without a memory cap\n'
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
step "audit"        uv run scripts/audit_deps.py
step "ruff check"   uv run ruff check
step "ruff format"  uv run ruff format --check
step "ty"           uv run ty check evlampiy
step "sast"         uvx --from semgrep==1.182.1 semgrep scan --config p/python --config p/dockerfile --config p/github-actions --metrics off --error
step "pytest"       "${capped[@]}" uv run pytest
step "shellcheck"   shellcheck scripts/*.sh

printf '\n'
if [ ${#failed[@]} -eq 0 ]; then
  printf '%sall gates passed%s\n' "$green" "$reset"
  exit 0
fi
printf '%sfailed:%s\n' "$red" "$reset"
printf '  %s\n' "${failed[@]}"
exit 1
