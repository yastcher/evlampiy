"""scripts/gate.sh runs exactly the checks CI runs, and never reports green over a failure."""

import re

import pytest

from tests.script_fixtures import REPO_ROOT

SCOPE_PROBE = "systemd-run --user --scope --quiet true"
GATE_COMMANDS = [
    SCOPE_PROBE,
    "uv lock --locked",
    "uv run scripts/audit_deps.py",
    "uv run ruff check",
    "uv run ruff format --check",
    "uv run ty check evlampiy",
    "uvx --from semgrep==1.182.1 semgrep scan --config p/python --config p/dockerfile --config p/github-actions"
    " --metrics off --error",
    "systemd-run --user --scope --quiet -p MemoryMax=2G -p MemorySwapMax=0 uv run pytest",
    "shellcheck scripts/gate.sh",
]


def test_gate_runs_every_check_in_order_and_passes(run_gate):
    result, commands = run_gate()

    assert commands == GATE_COMMANDS
    assert result.returncode == 0
    assert result.stdout.rstrip().endswith("all gates passed")


def test_one_failed_check_fails_the_gate_and_the_rest_still_run(run_gate):
    result, commands = run_gate(fail="uv run ty check evlampiy")

    assert commands == GATE_COMMANDS
    assert result.returncode == 1
    assert "all gates passed" not in result.stdout
    assert result.stdout.rstrip().endswith("failed:\n  ty")


def test_gate_checks_the_scripts_of_its_own_tree(run_gate):
    """Called from another directory, the gate still expands its glob in its own root."""
    _, commands = run_gate()

    assert commands[-1] == "shellcheck scripts/gate.sh"


def test_without_a_systemd_user_session_the_tests_run_uncapped_and_say_so(run_gate):
    """The devcontainer and macOS have no user scope to put the tests in: they run as CI runs them."""
    result, commands = run_gate(fail=SCOPE_PROBE)

    assert commands[-2] == "uv run pytest"
    assert result.stdout.splitlines()[0] == "note: no systemd user session, so pytest runs without a memory cap"
    assert result.returncode == 0


@pytest.mark.parametrize("args", [["pytest"], ["--all"]])
def test_gate_takes_no_arguments(run_gate, args):
    result, commands = run_gate(*args)

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert commands == []


def test_gate_mirrors_the_ci_job():
    """The CI job's commands, install steps aside: apt is the runner's business, `uv sync --locked`
    becomes `uv lock --locked` — the same lockfile question without rewriting the developer's
    environment — and the memory cap over the tests is a laptop's business."""
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    job = re.search(r"^  lint-and-test:\n(?P<body>(?:    .*\n|\n)+)", workflow, re.M)
    assert job is not None
    runs = re.findall(r"^\s+run: (.+)$", job["body"], re.M)
    ci = [
        "uv lock --locked" if run == "uv sync --locked" else run for run in runs if not run.startswith("sudo apt-get")
    ]

    steps = re.findall(r'^step "[^"]+"\s+(.+)$', (REPO_ROOT / "scripts" / "gate.sh").read_text(), re.M)
    gate = [command.removeprefix('"${capped[@]}" ') for command in steps]

    assert gate == ci
