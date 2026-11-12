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
#                    memory-capped scope, against one MongoDB started for it;
#                    about 11 minutes with two workers
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
# of its own (tests/db_fixtures.py) — rather than a container each. Capped in memory: a mutant
# can make code allocate without end, and the cap kills that worker, counted as died, instead
# of the desktop. The cap allows 1.2 GB for mutmut and its fork server and 0.5 GB per worker.
children=${MUTMUT_CHILDREN:-2}
if ! [[ $children =~ ^[1-9][0-9]*$ ]]; then
  echo "pre_release_qa: MUTMUT_CHILDREN must be a positive whole number, not '$children'" >&2
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
rm -rf mutants
TEST_MONGO_URI="mongodb://$(docker port "$mongo" 27017)/" \
  systemd-run --user --scope --quiet -p MemoryMax=$((1200 + 500 * children))M \
  -p MemorySwapMax=0 -p OOMPolicy=continue uv run mutmut run --max-children "$children"
uv run mutmut export-cicd-stats
uv run python scripts/mutation_ratchet.py mutants/mutmut-cicd-stats.json \
  --survived-max 195 --no-tests-max 49

echo "$tree" > "$stamp"
printf '\npre_release_qa: passed for tree %s\n' "$tree"
