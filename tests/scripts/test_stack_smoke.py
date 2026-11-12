"""scripts/stack_smoke.sh passes a stack only healthy and steady, and takes it down whatever happened."""

from tests.script_fixtures import REPO_ROOT

_UP = "docker compose up --detach --wait --wait-timeout 120"
_DOWN = "docker compose down --volumes --remove-orphans"
_INSPECT = "docker inspect --format {{.State.Status}} {{.RestartCount}}"
GREEN = [
    "docker build --quiet --tag evlampiy_notes_qa:qa .",
    _UP,
    "docker compose port evlampiy_notes 8000",
    "curl -fsS http://127.0.0.1:27999/health",
    "docker compose ps --quiet mongodb",
    f"{_INSPECT} mongodb-id",
    "docker compose ps --quiet evlampiy_notes",
    f"{_INSPECT} evlampiy_notes-id",
    _DOWN,
]


def test_a_healthy_stack_that_stays_up_passes_and_is_taken_down(run_stack):
    result, commands, _ = run_stack()

    assert result.returncode == 0, result.stderr
    assert commands == GREEN
    assert result.stdout.splitlines()[-1] == "stack: healthy, /health as expected, no restarts in 0s"


def test_the_stack_runs_as_a_project_of_its_own_on_the_qa_overlay(run_stack):
    _, _, compose = run_stack()

    assert compose == "evlampiy-qa docker-compose.yml:scripts/compose.qa.yml evlampiy_notes_qa:qa"


def test_a_container_that_restarted_fails_the_smoke_and_the_stack_still_goes_down(run_stack):
    result, commands, _ = run_stack(state="running 1")

    assert result.returncode == 1
    assert "stack: mongodb is 'running 1' (status, restarts) 0s after it was healthy" in result.stderr
    assert commands[-2:] == ["docker compose logs --tail 40 mongodb", _DOWN]


def test_an_unexpected_health_answer_fails_the_smoke(run_stack):
    result, commands, _ = run_stack(health='{"status":"ok","whatsapp":"on"}')

    assert result.returncode == 1
    assert 'stack: /health answered {"status":"ok","whatsapp":"on"}' in result.stderr
    assert commands[-1] == _DOWN


def test_a_stack_that_never_gets_healthy_shows_its_logs_before_it_goes(run_stack):
    result, commands, _ = run_stack(fail=_UP)

    assert result.returncode == 1
    assert commands[-2:] == ["docker compose logs --tail 40", _DOWN]


def test_the_overlay_keeps_the_developers_env_and_ports_out():
    """The developer's .env holds the production bot's token: polled from QA too, it would break production."""
    overlay = (REPO_ROOT / "scripts" / "compose.qa.yml").read_text()

    assert "    env_file: !reset []\n" in overlay
    assert '    ports: !override\n      - "127.0.0.1::8000"\n' in overlay
