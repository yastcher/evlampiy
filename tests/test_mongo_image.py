"""Every MongoDB the code meets runs the image production pins: newer 8.0 builds crash on its hosts."""

import re

import pytest

from tests.db_fixtures import compose_mongo_image
from tests.script_fixtures import REPO_ROOT

PRODUCTION = compose_mongo_image(REPO_ROOT / "docker-compose.yml")


def test_the_devcontainer_runs_the_production_image():
    assert compose_mongo_image(REPO_ROOT / ".devcontainer" / "docker-compose.dev.yml") == PRODUCTION


def test_ci_tests_against_the_production_image():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    service = re.search(r"^    services:\n      mongodb:\n        image: (\S+)$", workflow, re.M)

    assert service is not None
    assert service[1] == PRODUCTION


def _mongodb_service(compose: str) -> str:
    service = re.search(r"^  mongodb:\n((?:    .*\n|\n)*)", compose, re.M)
    assert service is not None
    return service[1]


@pytest.mark.parametrize(
    "compose", [REPO_ROOT / "docker-compose.yml", REPO_ROOT / ".devcontainer" / "docker-compose.dev.yml"]
)
def test_compose_gives_mongod_the_open_files_it_asks_for(compose):
    """Docker's default is 1024 open files; WiredTiger keeps one per collection and index, and at the limit mongod
    aborts with EMFILE — a test run's churn reached it in 320 clients."""
    limit = "    ulimits:\n      nofile:\n        soft: 64000\n        hard: 64000\n"

    assert limit in _mongodb_service(compose.read_text())


def test_ci_gives_mongod_the_open_files_it_asks_for():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()

    assert "--ulimit nofile=64000:64000" in workflow
