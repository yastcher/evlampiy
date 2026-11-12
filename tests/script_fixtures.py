"""Fixtures for the tests of the repository's own scripts: release, changelog and gate."""

import os
import pathlib
import shutil
import subprocess

import pytest

from scripts import prepare_release

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

_RELEASE_PYPROJECT = """\
[project]
name = "evlampiy"
version = "1.2.3"
dependencies = ["click==1.2.3"]

[tool.example]
version = "9.9.9"
"""

# A dependency on the project's own number: an edit anchored on the version alone would hit it.
_RELEASE_LOCK = """\
version = 1
requires-python = ">=3.14"

[[package]]
name = "click"
version = "1.2.3"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "evlampiy"
version = "1.2.3"
source = { virtual = "." }
"""

# The scaffold is the real one: closing the section drops exactly those lines.
_RELEASE_CHANGELOG = (
    "## [Unreleased]\n\n"
    + "\n".join(prepare_release.SCAFFOLD)
    + "\n\n### Fixed\n\n- The next fix.\n\n## [1.2.3] — 2026-10-05\n\n### Fixed\n\n- The fix.\n"
)

# Git for the release tests, deaf to the developer's own config (signing, hooks, templates).
_GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Release Test",
    "GIT_AUTHOR_EMAIL": "release@example.com",
    "GIT_COMMITTER_NAME": "Release Test",
    "GIT_COMMITTER_EMAIL": "release@example.com",
}


def git(cwd: pathlib.Path, *args: str) -> str:
    """Run git in `cwd` with the isolated config; return stdout."""
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=os.environ | _GIT_ENV, capture_output=True, text=True, check=True
    )
    return result.stdout


@pytest.fixture
def release_tree(tmp_path):
    """A project tree on version 1.2.3 with one entry waiting under [Unreleased]."""
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "pyproject.toml").write_text(_RELEASE_PYPROJECT)
    (tree / "uv.lock").write_text(_RELEASE_LOCK)
    (tree / "CHANGELOG.md").write_text(_RELEASE_CHANGELOG)
    return tree


@pytest.fixture
def release_repo(tmp_path, release_tree):
    """`release_tree` as a git repository on main, pushed to a bare origin, with the real
    release scripts in it. Returns (work tree, origin, run) where run(*args) runs release.sh."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    scripts = release_tree / "scripts"
    scripts.mkdir()
    for name in ("release.sh", "prepare_release.py", "release_from_tag.py"):
        shutil.copy2(REPO_ROOT / "scripts" / name, scripts / name)
    git(release_tree, "init", "-q", "-b", "main")
    git(release_tree, "add", "-A")
    git(release_tree, "commit", "-q", "-m", "init")
    git(release_tree, "remote", "add", "origin", str(origin))
    git(release_tree, "push", "-q", "-u", "origin", "main")

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [scripts / "release.sh", *args],
            cwd=release_tree,
            env=os.environ | _GIT_ENV,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    return release_tree, origin, run


@pytest.fixture
def run_gate(tmp_path):
    """Run a copy of the real scripts/gate.sh with every command it calls stubbed on PATH.

    Returns a callable: `run_gate(*args, fail="uv run pytest")` makes the `fail` command
    exit 1 and gives back the finished process and every command the gate invoked, in
    order. The gate is called from the real repository root, whose scripts/ holds more
    than the copy's: a glob expanded there instead of in the gate's own tree shows up in
    the logged shellcheck command.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    gate = scripts / "gate.sh"
    shutil.copy2(REPO_ROOT / "scripts" / "gate.sh", gate)
    stub = (
        "#!/usr/bin/env bash\n"
        'printf "%s %s\\n" "${0##*/}" "$*" >> "$GATE_LOG"\n'
        'if [ "${0##*/} $*" = "$GATE_FAIL" ]; then exit 1; fi\n'
    )
    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name in ("uv", "uvx", "shellcheck", "systemd-run"):
        (stubs / name).write_text(stub)
        (stubs / name).chmod(0o755)
    log = tmp_path / "commands.log"

    def run(*args: str, fail: str = "") -> tuple[subprocess.CompletedProcess[str], list[str]]:
        env = {"PATH": f"{stubs}:{os.environ['PATH']}", "GATE_LOG": str(log), "GATE_FAIL": fail}
        result = subprocess.run(
            [gate, *args],
            cwd=REPO_ROOT,
            env=os.environ | env,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        commands = log.read_text().splitlines() if log.exists() else []
        return result, commands

    return run
