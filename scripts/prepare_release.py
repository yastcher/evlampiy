#!/usr/bin/env python3
"""Bump the version and close `## [Unreleased]` under it: the edit a release commits.

    scripts/prepare_release.py patch           # 0.9.7 -> 0.9.8, writes the files
    scripts/prepare_release.py minor --check   # validates and prints 0.10.0, writes nothing

Prints the new version on stdout; `scripts/release.sh` reads it. The version lives in
pyproject.toml and in uv.lock's entry for the project itself, and both move together.
`## [Unreleased]` becomes `## [X.Y.Z] — YYYY-MM-DD` under a fresh `[Unreleased]`.
An `[Unreleased]` without entries is refused: that section is the release notes.
"""

import argparse
import datetime
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PARTS = ("patch", "minor", "major")
UNRELEASED = "## [Unreleased]"
SCAFFOLD = (
    "<!-- New entries go here, through scripts/changelog_add.py — never under a released version. -->",
    "<!-- Subsections, in order: Added / Changed / Fixed / Removed / Docs. -->",
)

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_SECTION = re.compile(r"^## \[(?P<version>[^\]]+)\]")
# The first `version = "..."` line is [project]'s; a pin further down must never be taken for it.
_PROJECT_VERSION = re.compile(r'^version = "[^"]*"$', re.M)


def next_version(current: str, part: str) -> str:
    match = _SEMVER.match(current)
    if match is None:
        raise SystemExit(f"pyproject.toml declares {current!r}, not an X.Y.Z version")
    major, minor, patch = map(int, match.groups())
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def close_unreleased(text: str, *, version: str, today: datetime.date) -> str:
    """Name the open section, open a fresh one above it. The hint comments stay with the open one."""
    lines = text.splitlines()
    if any((m := _SECTION.match(line)) and m["version"] == version for line in lines):
        raise SystemExit(f"CHANGELOG.md already has a section for {version}")
    top = next((i for i, line in enumerate(lines) if line.rstrip() == UNRELEASED), None)
    if top is None:
        raise SystemExit(
            f"CHANGELOG.md has no `{UNRELEASED}` section. The previous release opens it, "
            "so the last tag was cut by hand instead of through scripts/release.sh."
        )
    following = next((i for i in range(top + 1, len(lines)) if _SECTION.match(lines[i])), len(lines))
    # The scaffold is the tooling's and opens the next section; every other line is the maintainer's.
    kept = [line for line in lines[top + 1 : following] if line not in SCAFFOLD]
    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()
    if not any(line.startswith("- ") for line in kept):
        raise SystemExit(f"the `{UNRELEASED}` section has no entries: nothing to release")

    opened = [UNRELEASED, "", *SCAFFOLD, ""]
    closed = [f"## [{version}] — {today.isoformat()}", "", *kept, ""]
    return "\n".join(lines[:top] + opened + closed + lines[following:]) + "\n"


def set_project_version(pyproject: str, version: str) -> str:
    return _PROJECT_VERSION.sub(f'version = "{version}"', pyproject, count=1)


def set_locked_version(lock: str, name: str, version: str) -> str:
    """uv.lock's entry for the project itself, anchored on its name: a dependency that
    happens to sit on the same number is never touched."""
    entry = re.compile(rf'^(name = "{re.escape(name)}"\nversion = )"[^"]*"$', re.M)
    updated, count = entry.subn(rf'\g<1>"{version}"', lock, count=1)
    if count != 1:
        raise SystemExit(f"uv.lock has no entry for {name}")
    return updated


def prepare(root: pathlib.Path, part: str, *, today: datetime.date, write: bool) -> str:
    """Validate everything first, then write all three files, or nothing."""
    pyproject_path, lock_path, changelog_path = root / "pyproject.toml", root / "uv.lock", root / "CHANGELOG.md"
    pyproject = pyproject_path.read_text(encoding="utf-8")
    project = tomllib.loads(pyproject)["project"]
    version = next_version(project["version"], part)

    new_pyproject = set_project_version(pyproject, version)
    if tomllib.loads(new_pyproject)["project"]["version"] != version:
        raise SystemExit("the first `version =` line of pyproject.toml is not [project]'s")
    new_lock = set_locked_version(lock_path.read_text(encoding="utf-8"), project["name"], version)
    new_changelog = close_unreleased(changelog_path.read_text(encoding="utf-8"), version=version, today=today)

    if write:
        pyproject_path.write_text(new_pyproject, encoding="utf-8")
        lock_path.write_text(new_lock, encoding="utf-8")
        changelog_path.write_text(new_changelog, encoding="utf-8")
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("part", choices=PARTS)
    parser.add_argument("--check", action="store_true", help="validate and print the version, write nothing")
    args = parser.parse_args()

    # The local calendar date: a release cut after midnight is dated the day its author sees.
    today = datetime.datetime.now(datetime.UTC).astimezone().date()
    version = prepare(ROOT, args.part, today=today, write=not args.check)
    sys.stdout.write(f"{version}\n")


if __name__ == "__main__":
    main()
