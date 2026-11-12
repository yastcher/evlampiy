"""deploy/: a release goes out only after a dump, and stays only if it holds; otherwise the one before comes back."""

import pytest

from tests.script_fixtures import DEPLOY_IMAGE

_RELEASE = f"{DEPLOY_IMAGE}:v0.10.0"
_DUMP = "docker compose exec -T mongodb mongodump --quiet --archive --gzip"
_UP = "docker compose up --detach --remove-orphans"
_HEALTH = "curl -fsS --max-time 5 http://localhost:8000/health"
# /health does not ask mongodb: a database down for the whole minute still answers it.
_MONGO_DOWN = "/mongodb exited 139\\n/evlampiy_notes running 0"
_NAMES = "docker inspect --format {{.Name}} {{.State.Status}} {{.RestartCount}} c-mongo c-app"
GREEN = [
    _DUMP,
    "docker compose pull evlampiy_notes",
    _UP,
    _HEALTH,
    "docker compose ps --all --quiet",
    _NAMES,
    "docker compose ps --all --quiet",
    _NAMES,
    "docker compose ps --quiet evlampiy_notes",
    "docker inspect --format {{.Config.Image}} c-app",
    f"docker images --format {{{{.Repository}}}}:{{{{.Tag}}}} {DEPLOY_IMAGE}",
    f"docker rmi {DEPLOY_IMAGE}:v0.9.5",
    "docker image prune --force",
]


def _deploy(run, **env):
    return run("deploy.sh", DEPLOY_IMAGE, "v0.10.0", **env)


def test_a_release_that_holds_stays_and_only_its_predecessor_is_kept(deploy_server):
    server, run = deploy_server

    result, commands = _deploy(run)

    assert result.returncode == 0, result.stderr
    assert commands == GREEN
    assert (server / "docker-compose.yml").read_text() == "# v0.10.0's stack\n"
    assert (server / "docker-compose.v0.9.7.yml").read_text() == "# v0.9.7's stack\n"


def test_the_release_is_pinned_in_env_and_every_other_line_kept(deploy_server):
    server, run = deploy_server

    _deploy(run)

    assert (server / ".env").read_text() == (
        f"TELEGRAM_BOT_TOKEN=kept\nEVLAMPIY_IMAGE={DEPLOY_IMAGE}\nIMAGE_TAG=v0.10.0\n"
    )


def test_the_database_is_dumped_under_the_release_it_belongs_to(deploy_server):
    server, run = deploy_server

    _deploy(run)

    [archive] = (server / "backups").iterdir()
    assert archive.name.endswith("-v0.9.7.archive.gz")
    assert archive.read_text() == "dump of the database\n"


@pytest.mark.parametrize(
    "env",
    [
        {"DEPLOY_UNHEALTHY": "1"},
        {"DEPLOY_AFTER": "/mongodb running 0\\n/evlampiy_notes running 1"},
        {"DEPLOY_AFTER": "/mongodb exited 0\\n/evlampiy_notes running 0"},
        {"DEPLOY_BEFORE": _MONGO_DOWN, "DEPLOY_AFTER": _MONGO_DOWN},
        {"DEPLOY_RUNNING": f"{DEPLOY_IMAGE}:v0.9.7"},
    ],
    ids=["no /health", "a restart", "a container going down", "a container down throughout", "the old image"],
)
def test_a_release_that_does_not_hold_puts_the_one_before_back(deploy_server, env):
    server, run = deploy_server

    result, commands = _deploy(run, **env)

    assert result.returncode == 1
    assert "v0.10.0 did not hold — putting v0.9.7 back" in result.stderr
    assert (server / "docker-compose.yml").read_text() == "# v0.9.7's stack\n"
    assert "IMAGE_TAG=v0.9.7\n" in (server / ".env").read_text()
    assert commands.index("docker compose logs --tail 60") < len(commands) - commands[::-1].index(_UP) - 1


def test_a_failed_dump_stops_the_release_before_anything_changes(deploy_server):
    server, run = deploy_server

    result, commands = _deploy(run, DEPLOY_FAIL=_DUMP)

    assert result.returncode == 1
    assert commands == [_DUMP]
    assert (server / "docker-compose.yml").read_text() == "# v0.9.7's stack\n"
    assert list((server / "backups").iterdir()) == []


def test_the_first_release_has_nothing_to_dump_or_to_go_back_to(deploy_server):
    server, run = deploy_server
    (server / ".env").write_text("TELEGRAM_BOT_TOKEN=kept\n")

    result, commands = _deploy(run, DEPLOY_UNHEALTHY="1")

    assert result.returncode == 1
    assert _DUMP not in commands
    assert "putting" not in result.stderr


def test_a_rollback_without_the_releases_compose_file_refuses(deploy_server):
    _, run = deploy_server

    result, commands = run("rollback.sh", "v0.9.1")

    assert result.returncode == 1
    assert "no docker-compose.v0.9.1.yml here" in result.stderr
    assert commands == []


@pytest.mark.parametrize("release", ["", "../etc", "v1 v2"])
def test_a_release_name_that_could_walk_out_of_the_directory_is_refused(deploy_server, release):
    _, run = deploy_server

    result, commands = run("backup-db.sh", release)

    assert result.returncode == 2
    assert commands == []
