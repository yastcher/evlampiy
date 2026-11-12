"""CHANGELOG entries land in `[Unreleased]`, in the right subsection, and nowhere else."""

import re

import pytest

from scripts import changelog_add

from tests.script_fixtures import REPO_ROOT

OPEN = """\
## [Unreleased]

<!-- hint -->

### Added

- A.

### Fixed

- F.

## [0.9.7] — 2026-07-15

### Added

- Shipped.
"""


def _add(subsection: str, *, first: bool = False) -> str:
    return changelog_add.add_entry(OPEN, subsection=subsection, entry="- New.", first=first)


def test_entry_is_appended_to_its_subsection_as_a_tight_list():
    assert "### Added\n\n- A.\n- New.\n\n### Fixed" in _add("Added")


def test_top_puts_the_entry_first_under_the_heading():
    assert "### Fixed\n\n- New.\n- F.\n\n## [0.9.7]" in _add("Fixed", first=True)


@pytest.mark.parametrize(
    ("subsection", "expected"),
    [
        ("Changed", "- A.\n\n### Changed\n\n- New.\n\n### Fixed"),
        ("Removed", "- F.\n\n### Removed\n\n- New.\n\n## [0.9.7]"),
        ("Docs", "- F.\n\n### Docs\n\n- New.\n\n## [0.9.7]"),
    ],
)
def test_missing_subsection_is_created_in_documented_order(subsection, expected):
    assert expected in _add(subsection)


def test_subsection_ranked_first_goes_above_the_existing_ones():
    only_fixed = OPEN.replace("### Added\n\n- A.\n\n", "")

    result = changelog_add.add_entry(only_fixed, subsection="Added", entry="- New.")

    assert "<!-- hint -->\n\n### Added\n\n- New.\n\n### Fixed\n\n- F." in result


def test_first_entry_of_a_cycle_lands_below_the_hint_comments():
    fresh = "## [Unreleased]\n\n<!-- hint -->\n\n## [0.9.7] — 2026-07-15\n"

    result = changelog_add.add_entry(fresh, subsection="Fixed", entry="- New.")

    assert result == "## [Unreleased]\n\n<!-- hint -->\n\n### Fixed\n\n- New.\n\n## [0.9.7] — 2026-07-15\n"


def test_released_sections_are_never_touched():
    assert _add("Added").split("## [0.9.7]")[1] == OPEN.split("## [0.9.7]")[1]


def test_entry_into_a_released_top_section_is_refused():
    released = OPEN.replace("## [Unreleased]", "## [0.9.8] — 2026-11-01")

    with pytest.raises(SystemExit, match=r"not '## \[Unreleased\]'"):
        changelog_add.add_entry(released, subsection="Added", entry="- New.")


def test_changelog_without_sections_is_refused():
    with pytest.raises(SystemExit, match="no release sections"):
        changelog_add.add_entry("# Changelog\n", subsection="Added", entry="- New.")


def test_repository_changelog_is_open_at_the_top():
    """Between releases entries go under [Unreleased]: a branch never picks a version."""
    first = re.search(r"^## .*$", (REPO_ROOT / "CHANGELOG.md").read_text(), re.M)

    assert first is not None
    assert first.group(0) == "## [Unreleased]"
