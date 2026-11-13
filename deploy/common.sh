# shellcheck shell=bash
# What deploy.sh and rollback.sh share; sourced in the deploy directory, where .env and
# docker-compose.yml are.

# Pin a value in .env, every other line kept: Compose reads the release from there, so a
# later manual `docker compose up` runs the same release instead of drifting.
set_env() {
  local key="$1" value="$2"
  if grep -q "^$key=" .env 2>/dev/null; then
    sed -i "s|^$key=.*|$key=$value|" .env
  else
    echo "$key=$value" >> .env
  fi
}

env_value() {
  sed -n "s/^$1=//p" .env 2>/dev/null | tail -n 1
}

# The release answers /health within two minutes: it waits on mongodb's healthcheck first.
healthy() {
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 5 http://localhost:8000/health >/dev/null 2>&1; then
      return 0
    fi
    sleep 4
  done
  echo "deploy: /health did not answer in two minutes" >&2
  return 1
}

# Name, status and restarts of every container of the stack, one per line.
containers() {
  docker compose ps --all --quiet | xargs -r docker inspect --format '{{.Name}} {{.State.Status}} {{.RestartCount}}' | sort
}

# ...and then runs a minute with every container up and none restarted: a crash loop
# answers one probe between its crashes, and /health does not ask mongodb.
steady() {
  local before after
  before="$(containers)"
  sleep "${DEPLOY_OBSERVE_SECONDS:-60}"
  after="$(containers)"
  if [ -z "$after" ] || [ "$before" != "$after" ] || grep -qv ' running ' <<< "$after"; then
    echo "deploy: the stack did not hold for a minute; before, then after:" >&2
    printf '%s\n--\n%s\n' "$before" "$after" >&2
    return 1
  fi
}

# ...and the bot runs the image this release pinned, not a container left over.
runs_image() {
  local running
  running="$(docker inspect --format '{{.Config.Image}}' "$(docker compose ps --quiet evlampiy_notes)")"
  if [ "$running" != "$1" ]; then
    echo "deploy: evlampiy_notes runs $running, not $1" >&2
    return 1
  fi
}
