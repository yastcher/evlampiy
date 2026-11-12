#!/usr/bin/env bash
# Everything slower than a pull request can afford, run once before a release, on main.
# `scripts/release.sh` refuses to tag a tree this script has not passed.
#
#     mkdir -p tmp && scripts/pre_release_qa.sh > tmp/qa.log 2>&1
#
#   1. the gate — scripts/gate.sh: what CI runs on a push
#   2. CRAP     — scripts/crap.py over the coverage the gate's tests wrote
#
# On success it writes the tree hash into the git directory; `release.sh` compares it with
# the tree it is about to tag. Any stage that fails stops the run and leaves no stamp.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

stamp="$(git rev-parse --path-format=absolute --git-path pre_release_qa.ok)"
tree="$(git rev-parse 'HEAD^{tree}')"

if [ -n "$(git status --porcelain)" ]; then
  echo "pre_release_qa: the tree is dirty — a stamp would name a state nobody can check out" >&2
  exit 1
fi
# A stamp from an earlier run must not outlive a run that fails.
rm -f "$stamp"

stage() { printf '\n── %s\n' "$1"; }

stage "gate"
scripts/gate.sh

stage "CRAP"
# Complexity meeting missing tests, per function. The limit sat at the worst function when
# it was set, and only comes down: lower it as that function improves, never raise it to
# let a change in.
uv run python scripts/crap.py coverage.json --max 20

echo "$tree" > "$stamp"
printf '\npre_release_qa: passed for tree %s\n' "$tree"
