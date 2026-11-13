#!/usr/bin/env python3
"""Check a `vX.Y.Z` tag against the tree and print its release notes.

The tag is the release decision and the one copy of the version a person types, so the
release pipeline checks it before building anything, and `scripts/release.sh` asks the
same question before it pushes:

* the tag must name the version pyproject.toml declares;
* uv.lock must record that version for the project;
* CHANGELOG.md must have a non-empty `## [X.Y.Z]` section: it becomes the release notes.

    scripts/release_from_tag.py v0.10.0
    scripts/release_from_tag.py v0.10.0 --notes-file notes.md

Exits non-zero with a plain message on any mismatch. Standard library only, so it runs
on a bare python3 before any dependency is installed.
"""

import argparse
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_TAG = re.compile(r"^v(\d+\.\d+\.\d+)$")


def version_of_tag(tag: str) -> str:
    """`v0.10.0` -> `0.10.0`. Anything else is not a release tag and must not publish."""
    match = _TAG.match(tag)
    if match is None:
        raise SystemExit(f"not a release tag: {tag!r} (expected vX.Y.Z)")
    return match.group(1)


def declared_project(root: pathlib.Path) -> tuple[str, str]:
    """The project's (name, version) from pyproject.toml."""
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return project["name"], project["version"]


def locked_version(root: pathlib.Path, name: str) -> str:
    """The version uv.lock records for the project itself, anchored on its name."""
    entry = re.compile(rf'^name = "{re.escape(name)}"\nversion = "(?P<version>[^"]+)"$', re.M)
    match = entry.search((root / "uv.lock").read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"uv.lock has no entry for {name}")
    return match["version"]


def changelog_notes(root: pathlib.Path, version: str) -> str:
    """The body of the `## [X.Y.Z]` section, verbatim, without its heading."""
    text = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    start = re.search(rf"^## \[{re.escape(version)}\].*$", text, re.M)
    if start is None:
        raise SystemExit(f"CHANGELOG.md has no section for {version}: cut releases with scripts/release.sh")
    rest = text[start.end() :]
    end = re.search(r"^## ", rest, re.M)
    body = (rest[: end.start()] if end else rest).strip()
    if not body:
        raise SystemExit(f"the CHANGELOG section for {version} is empty")
    return body


def check(root: pathlib.Path, tag: str) -> str:
    """Refuse any disagreement between the tag and the tree; return the release notes."""
    version = version_of_tag(tag)
    name, declared = declared_project(root)
    if declared != version:
        raise SystemExit(f"tag {tag} disagrees with pyproject.toml ({declared}): cut releases with scripts/release.sh")
    locked = locked_version(root, name)
    if locked != version:
        raise SystemExit(f"tag {tag} disagrees with uv.lock ({locked})")
    return changelog_notes(root, version)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tag")
    parser.add_argument("--notes-file", type=pathlib.Path, help="write the notes here instead of stdout")
    args = parser.parse_args()

    notes = check(ROOT, args.tag)
    if args.notes_file:
        args.notes_file.write_text(f"{notes}\n", encoding="utf-8")
    else:
        sys.stdout.write(f"{notes}\n")


if __name__ == "__main__":
    main()
