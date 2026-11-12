"""The release pipeline in ci.yml: only a version tag ships, past a scan, to a server whose key is known."""

import re

import pytest

from tests.script_fixtures import REPO_ROOT

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI = (WORKFLOWS / "ci.yml").read_text()
ON_A_TAG = "if: startsWith(github.ref, 'refs/tags/v')"
# What makes ssh take any key a host presents: on a fresh runner, that is every connection.
TRUSTS_ANY_HOST_KEY = re.compile(r"StrictHostKeyChecking[ =]+(no|off|accept-new)\b", re.I)


def _job(name: str) -> str:
    match = re.search(rf"^  {name}:\n((?:    .*\n|\n)+)", CI, re.M)
    assert match is not None, f"no job {name!r} in ci.yml"
    return match[1]


def _step(job: str, name: str) -> str:
    match = re.search(rf"^      - name: {name}\n((?:        .*\n|\n)*)", _job(job), re.M)
    assert match is not None, f"no step {name!r} in the job {job!r}"
    return match[1]


@pytest.mark.parametrize("job", ["deploy", "release"])
def test_only_a_version_tag_deploys_and_publishes(job):
    assert re.search(rf"^    {re.escape(ON_A_TAG)}$", _job(job), re.M)


def test_a_pull_request_scans_the_image_and_only_a_tag_pushes_it():
    assert ON_A_TAG not in _step("image", "Scan the image")
    assert ON_A_TAG in _step("image", "Push the release image")


def test_the_image_is_scanned_before_it_is_pushed():
    image = _job("image")
    assert image.index("- name: Scan the image") < image.index("- name: Push the release image")


def test_the_scanner_is_pinned_by_digest():
    assert re.search(r"aquasecurity/trivy:[\d.]+@sha256:[0-9a-f]{64} ", _step("image", "Scan the image"))


def test_the_release_page_waits_for_the_deploy():
    assert "needs: deploy" in _job("release")


def test_the_deploy_trusts_the_host_key_from_its_secret():
    ssh = _step("deploy", "Set up SSH")
    assert "secrets.SSH_KNOWN_HOSTS" in ssh
    assert "StrictHostKeyChecking yes" in ssh


@pytest.mark.parametrize("workflow", sorted(WORKFLOWS.glob("*.yml")), ids=lambda path: path.name)
def test_no_workflow_takes_whatever_host_key_answers(workflow):
    assert TRUSTS_ANY_HOST_KEY.search(workflow.read_text()) is None


@pytest.mark.parametrize(
    "option", ["-o StrictHostKeyChecking=no", "-o StrictHostKeyChecking=accept-new", "  StrictHostKeyChecking off"]
)
def test_the_host_key_check_catches_each_way_of_turning_it_off(option):
    assert TRUSTS_ANY_HOST_KEY.search(option) is not None
