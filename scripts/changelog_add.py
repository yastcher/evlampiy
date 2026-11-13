#!/usr/bin/env python3
"""Add a CHANGELOG entry under `## [Unreleased]` — never under a released version.

Between releases the first section of CHANGELOG.md is always `## [Unreleased]`:
`scripts/release.sh` gives it a number at release time and opens a fresh one above it.
So an entry has exactly one place to go, and no branch ever picks a version number.

    scripts/changelog_add.py Fixed "- Voice notes longer than 20 s are no longer cut off"
    scripts/changelog_add.py Changed --top "- ..."     # first in its subsection
    scripts/changelog_add.py Docs --file entry.md

The entry is written verbatim and must already be a markdown bullet. A missing
subsection is created in the documented order; nothing else in the file is touched.
"""

import argparse
import pathlib
import re
import sys

# The order AGENTS.md documents; a new subsection is inserted so the section keeps it.
SUBSECTIONS = ("Added", "Changed", "Fixed", "Removed", "Docs")
UNRELEASED = "## [Unreleased]"

CHANGELOG = pathlib.Path(__file__).resolve().parents[1] / "CHANGELOG.md"

_SECTION = re.compile(r"^## \[")
_SUBSECTION = re.compile(r"^### (?P<name>.+?)\s*$")


def _skip_blank(body: list[str], at: int) -> int:
    while at < len(body) and not body[at].strip():
        at += 1
    return at


def _trim_blank(body: list[str], at: int, floor: int) -> int:
    while at > floor and not body[at - 1].strip():
        at -= 1
    return at


def add_entry(text: str, *, subsection: str, entry: str, first: bool = False) -> str:
    """Put `entry` into `subsection` of the `[Unreleased]` section: last, or first with `first`."""
    lines = text.splitlines()
    top = next((i for i, line in enumerate(lines) if _SECTION.match(line)), None)
    if top is None:
        raise SystemExit("CHANGELOG.md has no release sections at all")
    if lines[top].rstrip() != UNRELEASED:
        raise SystemExit(
            f"the top section is {lines[top]!r}, not {UNRELEASED!r}. A release opens the next "
            "section itself, so the last tag was cut by hand instead of through scripts/release.sh."
        )
    following = next((i for i in range(top + 1, len(lines)) if _SECTION.match(lines[i])), len(lines))
    body = lines[top + 1 : following]
    present = [(i, m["name"]) for i, line in enumerate(body) if (m := _SUBSECTION.match(line))]
    bullet = entry.rstrip("\n")

    # This file puts a blank line under each `###` heading and keeps the bullets below it
    # as one tight list: a blank line between two bullets would make the list loose.
    for i, name in present:
        if name != subsection:
            continue
        if first:
            body.insert(_skip_blank(body, i + 1), bullet)
        else:
            end = next((j for j, _ in present if j > i), len(body))
            body.insert(_trim_blank(body, end, i + 1), bullet)
        break
    else:
        rank = SUBSECTIONS.index(subsection)
        earlier = [i for i, name in present if name in SUBSECTIONS and SUBSECTIONS.index(name) < rank]
        at = len(body)
        if earlier:
            at = next((j for j, _ in present if j > earlier[-1]), len(body))
        elif present:
            at = present[0][0]
        body[_trim_blank(body, at, 0) : at] = ["", f"### {subsection}", "", bullet, ""]

    return "\n".join(lines[: top + 1] + body + lines[following:]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subsection", choices=SUBSECTIONS)
    parser.add_argument("entry", nargs="?", default="", help="the markdown bullet, verbatim")
    parser.add_argument("--file", type=pathlib.Path, help="read the bullet from this file instead")
    parser.add_argument("--top", action="store_true", help="put it first: user-facing above infrastructure")
    args = parser.parse_args()

    entry = args.file.read_text(encoding="utf-8") if args.file else args.entry
    if not entry.strip():
        raise SystemExit("nothing to add")
    if not entry.lstrip().startswith("- "):
        raise SystemExit("the entry must be a markdown bullet starting with '- '")

    CHANGELOG.write_text(
        add_entry(CHANGELOG.read_text(encoding="utf-8"), subsection=args.subsection, entry=entry, first=args.top),
        encoding="utf-8",
    )
    sys.stderr.write(f"added to ### {args.subsection}\n")


if __name__ == "__main__":
    main()
