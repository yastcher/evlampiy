#!/usr/bin/env bash
# Roll a release out, in the deploy directory on the server, where the release pipeline
# runs it over ssh after copying the release's docker-compose.yml into incoming/:
#
#     bash deploy/deploy.sh <image> <release>     # ghcr.io/yastcher/evlampiy_notes v0.10.0
#
# In order: dump the database, keep the running release's compose file under its name,
# put the new one in place and pin the release in .env, pull, start. Then the release has
# to answer /health, hold a minute with nothing restarted, and be the image that runs.
# If any of that fails, the release before it is put back and the deploy fails; when it
# holds, images older than those two go.
set -euo pipefail

image="${1:-}" release="${2:-}"
if [ -z "$image" ] || ! [[ $release =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "usage: ${0##*/} <image> <release>" >&2
  exit 2
fi
cd "$(dirname "$0")/.."
# shellcheck source=deploy/common.sh
. deploy/common.sh

if [ ! -f incoming/docker-compose.yml ]; then
  echo "deploy: no incoming/docker-compose.yml — the pipeline copies it there first" >&2
  exit 1
fi

previous="$(env_value IMAGE_TAG)"
if [ -n "$previous" ]; then
  bash deploy/backup-db.sh "$previous"
  cp docker-compose.yml "docker-compose.$previous.yml"
fi
mv incoming/docker-compose.yml docker-compose.yml
set_env EVLAMPIY_IMAGE "$image"
set_env IMAGE_TAG "$release"

# No `docker compose down`: only the bot's image changed, so Compose recreates the bot and
# leaves mongodb running unless its own definition changed.
if docker compose pull evlampiy_notes && docker compose up --detach --remove-orphans \
  && healthy && steady && runs_image "$image:$release"; then
  echo "deploy: $release is up and holding"
else
  # The failed release's own logs, before a rollback replaces its containers.
  docker compose logs --tail 60 >&2
  if [ -n "$previous" ]; then
    echo "deploy: $release did not hold — putting $previous back" >&2
    bash deploy/rollback.sh "$previous"
  fi
  exit 1
fi

# Every release keeps its tag, so `image prune` alone leaves them all; this one and the
# one before it stay, the rollback needs that. NEVER a volume prune: mongo_data is the database.
docker images --format '{{.Repository}}:{{.Tag}}' "$image" \
  | grep -vxF -e "$image:$release" -e "$image:${previous:-$release}" \
  | xargs -r docker rmi >/dev/null 2>&1 || true
docker image prune --force >/dev/null
