"""The compose files: the database is never published, and production's services come back on their own."""

import re
import subprocess

import pytest

from tests.script_fixtures import REPO_ROOT

COMPOSE_FILES = subprocess.run(
    ["git", "ls-files", "*compose*.yml"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
).stdout.split()


def _services(compose: str) -> dict[str, str]:
    """Each service's block of a compose file, by name."""
    body = re.split(r"^services:\n", compose, maxsplit=1, flags=re.M)[1]
    return dict(re.findall(r"^  ([\w-]+):\n((?:    .*\n|\n)*)", body, re.M))


@pytest.mark.parametrize("compose", COMPOSE_FILES)
def test_mongodb_is_never_published(compose):
    """MongoDB on a published port was found and broken into once: only the stack's own network reaches it."""
    mongodb = _services((REPO_ROOT / compose).read_text())["mongodb"]

    assert "    ports:" not in mongodb


def test_production_publishes_ports_on_the_loopback_only():
    """Docker opens a published port past the host's firewall, as it opened MongoDB's: the internet reaches
    the app through the TLS proxy on the host, and nothing but the host reaches the app."""
    published = [
        entry
        for block in _services((REPO_ROOT / "docker-compose.yml").read_text()).values()
        for ports in re.findall(r"^    ports:\n((?:      .*\n)+)", block, re.M)
        for entry in re.findall(r'^      - "([^"]+)"', ports, re.M)
    ]

    assert published == ["127.0.0.1:8000:8000"]


@pytest.mark.parametrize("service", ["mongodb", "evlampiy_notes"])
def test_every_production_service_restarts_on_its_own(service):
    """A stack that comes back half-way after a crash or a reboot hides the failure behind the live container."""
    block = _services((REPO_ROOT / "docker-compose.yml").read_text())[service]

    assert re.search(r"^    restart: (always|unless-stopped)$", block, re.M) is not None
