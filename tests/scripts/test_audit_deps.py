"""The dependency audit (`scripts/audit_deps.py`): a pin with an advisory fails it and names its fix, an acceptance
holds through its day and not after, one that matches nothing fails, and a scanner that cannot answer fails it closed.
The scanners are faked in their real report shapes: what is under test is how the reports are read."""

import datetime
import json
import subprocess

import pytest

from scripts import audit_deps

_TODAY = datetime.date(2026, 11, 11)
_CLEAN = {"dependencies": [{"name": "httpx", "version": "0.28.1", "vulns": []}], "fixes": []}
_ADVISORY = {"id": "PYSEC-2026-0001", "fix_versions": ["3.14.6"], "aliases": ["CVE-2026-0001", "GHSA-aaaa-bbbb-cccc"]}
_VULNERABLE = {
    "dependencies": [
        {"name": "httpx", "version": "0.28.1", "vulns": []},
        {"name": "aiohttp", "version": "3.14.5", "vulns": [_ADVISORY]},
    ],
    "fixes": [],
}
_VULNERABLE_LINE = "aiohttp 3.14.5 -> 3.14.6 (PYSEC-2026-0001, CVE-2026-0001, GHSA-aaaa-bbbb-cccc)"


def _scanners(report: dict, *, export_exit: int = 0, audit_exit: int | None = None, audit_stdout: str | None = None):
    def run(argv: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        if argv[:2] == ["uv", "export"]:
            return subprocess.CompletedProcess(argv, export_exit, stdout="pins", stderr="boom" if export_exit else "")
        code = audit_exit if audit_exit is not None else int(any(dep.get("vulns") for dep in report["dependencies"]))
        stdout = json.dumps(report) if audit_stdout is None else audit_stdout
        return subprocess.CompletedProcess(argv, code, stdout=stdout, stderr="boom" if code > 1 else "")

    return run


def test_a_pin_with_an_advisory_fails_the_audit_and_names_its_fix(capsys):
    assert audit_deps.main(_scanners(_VULNERABLE), today=_TODAY) == 1
    assert capsys.readouterr().out.splitlines() == [_VULNERABLE_LINE, "1 problem(s) in uv.lock"]


def test_a_lock_without_advisories_passes(capsys):
    assert audit_deps.main(_scanners(_CLEAN), today=_TODAY) == 0
    assert capsys.readouterr().out.splitlines() == ["no known vulnerabilities in uv.lock"]


@pytest.mark.parametrize(
    ("until", "expected"),
    [
        (_TODAY, []),
        (_TODAY - datetime.timedelta(days=1), [f"{_VULNERABLE_LINE} — accepted until 2026-11-10, expired"]),
    ],
    ids=["through its day", "the day after"],
)
def test_an_acceptance_holds_through_its_day_and_not_after(until, expected):
    accepted = {"GHSA-aaaa-bbbb-cccc": audit_deps.Accepted(reason="no fix reachable yet", until=until)}

    assert audit_deps.problems(audit_deps.findings(_VULNERABLE), accepted, _TODAY) == expected


def test_an_acceptance_that_matches_nothing_fails():
    accepted = {"PYSEC-2025-0042": audit_deps.Accepted(reason="fixed upstream since", until=_TODAY)}

    assert audit_deps.problems(audit_deps.findings(_CLEAN), accepted, _TODAY) == [
        "accepted PYSEC-2025-0042 matches nothing any more — remove it"
    ]


@pytest.mark.parametrize(
    ("scanners", "said"),
    [
        (_scanners(_CLEAN, export_exit=2), "uv export exited 2: boom"),
        (_scanners(_CLEAN, audit_exit=2), "pip-audit exited 2: boom"),
        (_scanners(_CLEAN, audit_stdout="Traceback"), "the scanner's report is not JSON"),
        (
            _scanners({"dependencies": [{"name": "evlampiy", "skip_reason": "not on PyPI"}]}),
            "evlampiy was not audited: not on PyPI",
        ),
    ],
    ids=["export failed", "scanner failed", "report garbled", "a package skipped"],
)
def test_a_scanner_that_cannot_answer_fails_the_audit_closed(capsys, scanners, said):
    assert audit_deps.main(scanners, today=_TODAY) == 2
    assert capsys.readouterr().out.startswith(f"audit did not run: {said}")


def test_the_lock_is_audited_as_it_pins_from_the_repository_root():
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs.get("cwd")))
        return _scanners(_CLEAN)(argv, **kwargs)

    audit_deps.main(run, today=_TODAY)

    export, cwd = calls[0]
    assert ("--frozen" in export, cwd) == (True, audit_deps.REPO_ROOT)
