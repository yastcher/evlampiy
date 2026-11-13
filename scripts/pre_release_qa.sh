#!/usr/bin/env bash
# Everything slower than a pull request can afford, run once before a release, on main.
# `scripts/release.sh` refuses to tag a tree this script has not passed.
#
#     mkdir -p tmp && scripts/pre_release_qa.sh > tmp/qa.log 2>&1
#
#   1. the gate    — scripts/gate.sh: what CI runs on a push
#   2. CRAP        — scripts/crap.py over the coverage the gate's tests wrote
#   3. stack       — scripts/stack_smoke.sh: the release image and MongoDB in a stack of
#                    their own, healthy and not restarting a minute later
#   4. mutation    — mutmut over the slice in [tool.mutmut], from scratch, in a
#                    memory-capped scope, against one MongoDB started for it, with as
#                    many workers as the free memory fits; a mutant killed or timed out
#                    beside others runs again alone; about 11 minutes with two workers
#
# Needs Docker and a systemd user session.
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

stage "stack"
scripts/stack_smoke.sh

stage "mutation"
# Every function of the slice in [tool.mutmut], changed in small ways, against the tests that
# cover it; survivors and untested mutants only come down. From scratch: mutmut keeps a copied
# file unmutated when only the slice changed. mutmut runs a test session per mutant, so they
# share one MongoDB of the image production runs, started here — each session takes a database
# no other session holds (tests/db_fixtures.py) — rather than a container each. Capped in memory: a mutant
# can make code allocate without end, and the cap kills that worker instead of the desktop.
# The cap allows 1.2 GB for mutmut and its fork server and 0.5 GB per worker, and it protects
# only while that much is free: a run started with less lets the kernel kill the desktop
# before the cap is reached, as it did twice on an 8 GB laptop. So the workers are as many as
# the memory available fits beside the MongoDB's 0.5 GB, two at most, and none means no run.
if [ -n "${MUTMUT_CHILDREN:-}" ] && ! [[ $MUTMUT_CHILDREN =~ ^[1-9][0-9]*$ ]]; then
  echo "pre_release_qa: MUTMUT_CHILDREN must be a positive whole number, not '$MUTMUT_CHILDREN'" >&2
  exit 1
fi
workers_that_fit() {
  local available fit
  available="$(free -m | awk '/^Mem:/ {print $7}')"
  fit=$(((available - 1200 - 512) / 500))
  echo $((fit > 0 ? fit : 0))
}
fit="$(workers_that_fit)"
if ((fit < 1)); then
  echo "pre_release_qa: the memory available fits no mutation worker: close something and run again" >&2
  exit 1
fi
children=${MUTMUT_CHILDREN:-$((fit < 2 ? fit : 2))}
if ((children > fit)); then
  echo "pre_release_qa: the memory available fits only $fit of the $children mutation workers asked for" >&2
  exit 1
fi
image="$(sed -n '/^  mongodb:/,/^  [a-z]/{s/^    image: //p}' docker-compose.yml)"
mongo="evlampiy-qa-mongo-$$"
# 64000 open files, as MongoDB asks: at Docker's 1024 the mutants' churn of databases and
# indexes made mongod abort (EMFILE) a few hundred sessions in.
docker run -d --rm --name "$mongo" -p 127.0.0.1::27017 --memory 512m --memory-swap 512m \
  --ulimit nofile=64000:64000 \
  "$image" --wiredTigerCacheSizeGB 0.25 >/dev/null
trap 'docker stop "$mongo" >/dev/null 2>&1 || true' EXIT
ready=0
for _ in $(seq 1 30); do
  if docker exec "$mongo" mongosh --quiet --eval 'db.runCommand({ping: 1}).ok' 2>/dev/null | grep -qx 1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "pre_release_qa: the MongoDB for the mutants did not answer in 30 seconds" >&2
  exit 1
fi
# Once the MongoDB is gone, every mutant after it times out, and a timeout counts as killed: the
# run would pass while testing nothing. Asked after each mutmut run, before its counts are read.
# 2026-11-12: its memory cap killed mongod at mutant 360 of 884, and all 228 after it timed out.
mongo_still_running() {
  if [ "$(docker inspect --format '{{.State.Running}}' "$mongo" 2>/dev/null)" != true ]; then
    echo "pre_release_qa: the MongoDB for the mutants died during the run, so its counts are no verdict (journalctl -k says why)" >&2
    exit 1
  fi
}
rm -rf mutants
mongo_uri="mongodb://$(docker port "$mongo" 27017)/"
TEST_MONGO_URI="$mongo_uri" \
  systemd-run --user --scope --quiet -p MemoryMax=$((1200 + 500 * children))M \
  -p MemorySwapMax=0 -p OOMPolicy=continue uv run mutmut run --max-children "$children"
mongo_still_running
# The cap is one for the whole run, and the kernel kills its largest process, which need not
# be the mutant that allocated: whatever died or timed out beside others is judged again,
# alone, so a survivor cannot hide among the runaways. The statuses are read first, so a
# failing `mutmut results` stops the run instead of reading as nothing to run again.
results="$(uv run mutmut results --all true)"
mapfile -t again < <(awk -F': ' '$2 == "segfault" || $2 == "timeout" {sub(/^ +/, "", $1); print $1}' <<<"$results")
if ((${#again[@]})); then
  if (($(workers_that_fit) < 1)); then
    echo "pre_release_qa: ${#again[@]} mutants to run again alone, and the memory available fits no worker: close something and run again" >&2
    exit 1
  fi
  TEST_MONGO_URI="$mongo_uri" \
    systemd-run --user --scope --quiet -p MemoryMax=1700M \
    -p MemorySwapMax=0 -p OOMPolicy=continue uv run mutmut run --max-children 1 "${again[@]}"
  mongo_still_running
fi
uv run mutmut export-cicd-stats
uv run python scripts/mutation_ratchet.py mutants/mutmut-cicd-stats.json \
  --survived-max 194 --no-tests-max 49

echo "$tree" > "$stamp"
printf '\npre_release_qa: passed for tree %s\n' "$tree"
