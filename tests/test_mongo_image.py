"""Every MongoDB the code meets runs the image production pins: newer 8.0 builds crash on its hosts."""

import re

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
