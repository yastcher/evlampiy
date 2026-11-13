#!/usr/bin/env bash
# The release image in a stack of its own: docker-compose.yml with scripts/compose.qa.yml on
# top, under a project name no other stack uses. Passes when both containers come up
# healthy, /health answers as it should, and a minute later neither has restarted — the
# window in which mongod used to die, and a crash-looping bot would show.
#
#     scripts/stack_smoke.sh
#
# Needs Docker. Leaves nothing behind: the stack and its database volume go whatever the
# outcome; the image keeps one tag, so the next build replaces it.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

export COMPOSE_PROJECT_NAME=evlampiy-qa
export COMPOSE_FILE=docker-compose.yml:scripts/compose.qa.yml
export EVLAMPIY_IMAGE=evlampiy_notes_qa IMAGE_TAG=qa
# How long both containers must run without a restart once healthy: past the half minute
# after startup in which mongod 8.0.5+ crashed.
observe=${STACK_OBSERVE_SECONDS:-60}
# No WhatsApp credentials in this stack, so the webhook is off and says so.
expected='{"status":"ok","whatsapp":"off"}'

trap 'docker compose down --volumes --remove-orphans >/dev/null 2>&1 || true' EXIT

docker build --quiet --tag "$EVLAMPIY_IMAGE:$IMAGE_TAG" . >/dev/null
if ! docker compose up --detach --wait --wait-timeout 120; then
  # The trap takes the stack down, its logs with it: they go out first.
  docker compose logs --tail 40 >&2
  exit 1
fi

health="$(curl -fsS "http://$(docker compose port evlampiy_notes 8000)/health")"
if [ "$health" != "$expected" ]; then
  echo "stack: /health answered $health, not $expected" >&2
  exit 1
fi

sleep "$observe"
for service in mongodb evlampiy_notes; do
  state="$(docker inspect --format '{{.State.Status}} {{.RestartCount}}' "$(docker compose ps --quiet "$service")")"
  if [ "$state" != "running 0" ]; then
    echo "stack: $service is '$state' (status, restarts) ${observe}s after it was healthy" >&2
    docker compose logs --tail 40 "$service" >&2
    exit 1
  fi
done
echo "stack: healthy, /health as expected, no restarts in ${observe}s"
