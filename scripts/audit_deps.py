#!/usr/bin/env python3
"""Known vulnerabilities in what uv.lock pins, every group included: `uv run scripts/audit_deps.py`.

Exit 1 when a pinned package carries an advisory no live acceptance covers, or an acceptance
matches nothing any more; exit 2 when the scanner could not answer — an audit that did not run
is not a clean one. The lock is audited exactly as it pins, hashes included, so nothing is
resolved or installed.
"""

import dataclasses
import datetime
import json
import pathlib
import subprocess
import sys
import typing
from collections.abc import Callable, Mapping, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_STDERR_TAIL_CHARS = 500


@dataclasses.dataclass(frozen=True)
class Accepted:
    reason: str
    until: datetime.date


# An advisory we live with, under any of its ids (GHSA, PYSEC, CVE): why, and the day it is looked at again.
ACCEPTED: dict[str, Accepted] = {}


@dataclasses.dataclass(frozen=True)
class Finding:
    package: str
    version: str
    ids: tuple[str, ...]
    fix: str

    def line(self) -> str:
        return f"{self.package} {self.version} -> {self.fix or 'no fix yet'} ({', '.join(self.ids)})"


class ScanError(RuntimeError):
    pass


Run = Callable[..., subprocess.CompletedProcess[str]]


def findings(report: Mapping[str, typing.Any]) -> list[Finding]:
    found = []
    for dependency in report["dependencies"]:
        if reason := dependency.get("skip_reason"):
            raise ScanError(f"{dependency['name']} was not audited: {reason}")
        for vuln in dependency.get("vulns", []):
            fix = ", ".join(vuln.get("fix_versions", []))
            found.append(
                Finding(dependency["name"], dependency["version"], (vuln["id"], *vuln.get("aliases", [])), fix)
            )
    return found


def problems(found: Sequence[Finding], accepted: Mapping[str, Accepted], today: datetime.date) -> list[str]:
    """What fails the audit: a finding no live acceptance covers, and an acceptance nothing carries any more."""
    lines = []
    for finding in found:
        covering = [accepted[advisory] for advisory in finding.ids if advisory in accepted]
        if any(acceptance.until >= today for acceptance in covering):
            continue
        lines.append(finding.line() + (f" — accepted until {covering[0].until}, expired" if covering else ""))
    carried = {advisory for finding in found for advisory in finding.ids}
    lines += [
        f"accepted {advisory} matches nothing any more — remove it" for advisory in accepted if advisory not in carried
    ]
    return lines


def scan(run: Run) -> list[Finding]:
    export = ["uv", "export", "--quiet", "--frozen", "--no-emit-project", "--format", "requirements-txt"]
    pins = _answer(run(export, cwd=REPO_ROOT, capture_output=True, text=True), "uv export")
    audit = [sys.executable, "-m", "pip_audit", "--disable-pip", "--require-hashes", "--progress-spinner", "off"]
    result = run([*audit, "-f", "json", "-r", "/dev/stdin"], input=pins, capture_output=True, text=True)
    # pip-audit exits 1 when it finds something, and that is an answer.
    return findings(_json(_answer(result, "pip-audit", finding=1)))


def _answer(result: subprocess.CompletedProcess[str], where: str, *, finding: int | None = None) -> str:
    if result.returncode not in (0, finding):
        raise ScanError(f"{where} exited {result.returncode}: {result.stderr.strip()[-_STDERR_TAIL_CHARS:]}")
    return result.stdout


def _json(text: str) -> dict[str, typing.Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScanError(f"the scanner's report is not JSON: {exc}") from exc


def main(run: Run = subprocess.run, today: datetime.date | None = None) -> int:
    try:
        found = scan(run)
    except ScanError as exc:
        print(f"audit did not run: {exc}")
        return 2
    lines = problems(found, ACCEPTED, today or datetime.datetime.now(datetime.UTC).date())
    for line in lines:
        print(line)
    print(f"{len(lines)} problem(s) in uv.lock" if lines else "no known vulnerabilities in uv.lock")
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main())
