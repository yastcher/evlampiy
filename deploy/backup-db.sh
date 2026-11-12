#!/usr/bin/env bash
# Dump the database before a release touches it, in the deploy directory:
#
#     bash deploy/backup-db.sh <release>     # the release the data belongs to, e.g. v0.10.0
#
# mongodump's own gzipped archive, streamed out of the running mongodb container, so the
# host needs nothing installed. The newest ten are kept. To restore one:
#
#     docker compose exec -T mongodb mongorestore --archive --gzip --drop < backups/<file>
set -euo pipefail

release="${1:-}"
# It names a file: a tag or a commit hash, nothing that walks out of backups/.
if ! [[ $release =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "usage: ${0##*/} <release>   (letters, digits, '.', '_' and '-')" >&2
  exit 2
fi
cd "$(dirname "$0")/.."
keep=10

mkdir -p backups
archive="backups/mongo-$(date -u +%Y%m%dT%H%M%SZ)-$release.archive.gz"
# A dump that failed half-way must not stay behind looking like a backup.
if ! docker compose exec -T mongodb mongodump --quiet --archive --gzip > "$archive.partial"; then
  rm -f "$archive.partial"
  echo "backup: mongodump failed, so no release goes out" >&2
  exit 1
fi
mv "$archive.partial" "$archive"
echo "backup: $archive"

find backups -maxdepth 1 -name 'mongo-*.archive.gz' -printf '%T@ %p\n' | sort -rn | tail -n +$((keep + 1)) \
  | cut -d' ' -f2- | xargs -r rm -f --
