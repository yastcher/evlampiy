#!/usr/bin/env bash
# Put a release that ran before back, in the deploy directory — by hand, or by deploy.sh
# when a release does not come up:
#
#     bash deploy/rollback.sh <release>      # e.g. v0.9.7
#
# The compose file that release ran with was kept as docker-compose.<release>.yml when the
# next one arrived: a rollback runs that release's own file, not today's. Its image is
# still on the host (deploy.sh keeps the one before the current) or in the registry. The
# database is not rolled back: a dump to restore by hand is in backups/.
set -euo pipefail

release="${1:-}"
if ! [[ $release =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "usage: ${0##*/} <release>" >&2
  exit 2
fi
cd "$(dirname "$0")/.."
# shellcheck source=deploy/common.sh
. deploy/common.sh

saved="docker-compose.$release.yml"
if [ ! -f "$saved" ]; then
  echo "rollback: no $saved here — that release's compose file was never kept" >&2
  exit 1
fi
cp "$saved" docker-compose.yml
set_env IMAGE_TAG "$release"
docker compose up --detach --remove-orphans
healthy
echo "rollback: $release is running again"
