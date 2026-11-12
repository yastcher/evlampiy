"""A release moves every copy of the version at once, and its tag must agree with all of them."""

import datetime

import pytest

from scripts import prepare_release, release_from_tag

from tests.script_fixtures import REPO_ROOT, git

TODAY = datetime.date(2026, 11, 11)
SCAFFOLD = "\n".join(prepare_release.SCAFFOLD)


# --- prepare_release ---


@pytest.mark.parametrize(
    ("current", "part", "expected"),
    [
        ("1.2.3", "patch", "1.2.4"),
        ("1.2.3", "minor", "1.3.0"),
        ("1.2.3", "major", "2.0.0"),
        ("0.9.9", "patch", "0.9.10"),
        ("0.9.9", "minor", "0.10.0"),
    ],
)
def test_next_version(current, part, expected):
    assert prepare_release.next_version(current, part) == expected


@pytest.mark.parametrize("current", ["1.2", "1.2.3rc1", "v1.2.3"])
def test_a_version_that_is_not_xyz_is_refused(current):
    with pytest.raises(SystemExit, match=r"not an X\.Y\.Z version"):
        prepare_release.next_version(current, "patch")


def test_prepare_moves_every_copy_and_the_tag_check_accepts_the_result(release_tree):
    """The two halves of a release meet: what prepare writes is exactly what the tag check reads."""
    version = prepare_release.prepare(release_tree, "patch", today=TODAY, write=True)

    assert version == "1.2.4"
    pyproject = (release_tree / "pyproject.toml").read_text()
    assert 'name = "evlampiy"\nversion = "1.2.4"' in pyproject
    assert '[tool.example]\nversion = "9.9.9"' in pyproject
    lock = (release_tree / "uv.lock").read_text()
    assert 'name = "evlampiy"\nversion = "1.2.4"' in lock
    assert 'name = "click"\nversion = "1.2.3"' in lock
    assert release_from_tag.check(release_tree, "v1.2.4") == "### Fixed\n\n- The next fix."


def test_prepare_names_the_open_section_and_opens_a_fresh_one(release_tree):
    prepare_release.prepare(release_tree, "minor", today=TODAY, write=True)

    changelog = (release_tree / "CHANGELOG.md").read_text()
    assert changelog.startswith(
        "## [Unreleased]\n\n"
        + "\n".join(prepare_release.SCAFFOLD)
        + "\n\n## [1.3.0] — 2026-11-11\n\n### Fixed\n\n- The next fix.\n\n## [1.2.3]"
    )


def test_check_mode_writes_nothing(release_tree):
    before = {path.name: path.read_text() for path in release_tree.iterdir()}

    version = prepare_release.prepare(release_tree, "major", today=TODAY, write=False)

    assert version == "2.0.0"
    assert {path.name: path.read_text() for path in release_tree.iterdir()} == before


def test_a_refusal_leaves_every_file_as_it_was(release_tree):
    lock = release_tree / "uv.lock"
    lock.write_text(lock.read_text().replace('name = "evlampiy"', 'name = "other"'))
    pyproject = (release_tree / "pyproject.toml").read_text()

    with pytest.raises(SystemExit, match=r"uv\.lock has no entry for evlampiy"):
        prepare_release.prepare(release_tree, "patch", today=TODAY, write=True)
    assert (release_tree / "pyproject.toml").read_text() == pyproject


def test_an_unreleased_section_with_only_the_scaffold_is_refused():
    empty = f"## [Unreleased]\n\n{SCAFFOLD}\n\n## [1.2.3] — 2026-10-05\n\n- x\n"

    with pytest.raises(SystemExit, match="no entries: nothing to release"):
        prepare_release.close_unreleased(empty, version="1.2.4", today=TODAY)


def test_an_unreleased_section_of_headings_without_entries_is_refused():
    headings = f"## [Unreleased]\n\n{SCAFFOLD}\n\n### Fixed\n\n## [1.2.3] — 2026-10-05\n\n- x\n"

    with pytest.raises(SystemExit, match="no entries: nothing to release"):
        prepare_release.close_unreleased(headings, version="1.2.4", today=TODAY)


def test_a_comment_of_the_maintainers_own_goes_out_with_the_entries():
    """The scaffold is the only thing the tooling put there: closing drops it and keeps every other line."""
    text = (
        f"## [Unreleased]\n\n{SCAFFOLD}\n\n### Fixed\n\n<!-- verify on staging first -->\n- The fix.\n\n"
        "## [1.2.3] — 2026-10-05\n\n- x\n"
    )

    closed = prepare_release.close_unreleased(text, version="1.2.4", today=TODAY)

    assert (
        "## [1.2.4] — 2026-11-11\n\n### Fixed\n\n<!-- verify on staging first -->\n- The fix.\n\n## [1.2.3]" in closed
    )


def test_a_version_that_already_has_a_section_is_refused(release_tree):
    text = (release_tree / "CHANGELOG.md").read_text()

    with pytest.raises(SystemExit, match=r"already has a section for 1\.2\.3"):
        prepare_release.close_unreleased(text, version="1.2.3", today=TODAY)


def test_a_changelog_without_unreleased_is_refused(release_tree):
    text = (release_tree / "CHANGELOG.md").read_text().replace("## [Unreleased]", "## [1.2.4] — 2026-11-01")

    with pytest.raises(SystemExit, match=r"no `## \[Unreleased\]` section"):
        prepare_release.close_unreleased(text, version="1.2.5", today=TODAY)


# --- release_from_tag ---


def test_matching_tag_yields_its_section_as_notes(release_tree):
    assert release_from_tag.check(release_tree, "v1.2.3") == "### Fixed\n\n- The fix."


@pytest.mark.parametrize("tag", ["1.2.3", "v1.2", "v1.2.3-rc1"])
def test_anything_but_vxyz_is_not_a_release_tag(release_tree, tag):
    with pytest.raises(SystemExit, match="not a release tag"):
        release_from_tag.check(release_tree, tag)


@pytest.mark.parametrize(
    ("path", "old", "new", "message"),
    [
        ("pyproject.toml", 'version = "1.2.3"', 'version = "1.2.4"', r"pyproject\.toml \(1\.2\.4\)"),
        (
            "uv.lock",
            'name = "evlampiy"\nversion = "1.2.3"',
            'name = "evlampiy"\nversion = "1.2.2"',
            r"uv\.lock \(1\.2\.2\)",
        ),
        ("CHANGELOG.md", "## [1.2.3] — 2026-10-05", "## [1.2.2] — 2026-10-05", r"no section for 1\.2\.3"),
        ("CHANGELOG.md", "### Fixed\n\n- The fix.\n", "", r"section for 1\.2\.3 is empty"),
    ],
    ids=["pyproject", "uv.lock", "no section", "empty section"],
)
def test_one_disagreeing_copy_refuses_the_tag(release_tree, path, old, new, message):
    target = release_tree / path
    target.write_text(target.read_text().replace(old, new, 1))

    with pytest.raises(SystemExit, match=message):
        release_from_tag.check(release_tree, "v1.2.3")


def test_repository_versions_agree():
    """Only scripts/release.sh writes the version, all copies at once: a PR bumping one fails here."""
    name, declared = release_from_tag.declared_project(REPO_ROOT)

    assert release_from_tag.locked_version(REPO_ROOT, name) == declared


# --- release.sh ---


def test_release_pushes_main_then_the_tag(release_repo):
    work, origin, run = release_repo

    result = run("patch")

    assert result.returncode == 0, result.stderr
    assert git(origin, "log", "-1", "--format=%s", "main").strip() == "chore(release): 1.2.4"
    assert git(origin, "rev-parse", "v1.2.4^{commit}") == git(origin, "rev-parse", "main")
    assert git(work, "status", "--porcelain") == ""
    assert "### Fixed\n\n- The next fix." in result.stdout


@pytest.mark.parametrize("args", [(), ("hotfix",)])
def test_release_without_a_part_prints_usage(release_repo, args):
    _, origin, run = release_repo

    result = run(*args)

    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert git(origin, "tag") == ""


def test_release_refuses_a_dirty_tree(release_repo):
    work, origin, run = release_repo
    (work / "CHANGELOG.md").write_text("edited\n")

    result = run("patch")

    assert result.returncode == 1
    assert "dirty" in result.stderr
    assert git(origin, "tag") == ""


def test_release_refuses_a_branch_other_than_main(release_repo):
    work, origin, run = release_repo
    git(work, "switch", "-q", "-c", "feature")

    result = run("patch")

    assert result.returncode == 1
    assert "not 'feature'" in result.stderr
    assert git(origin, "tag") == ""


def test_release_refuses_history_origin_does_not_have(release_repo):
    work, origin, run = release_repo
    git(work, "commit", "-q", "--allow-empty", "-m", "local only")

    result = run("patch")

    assert result.returncode == 1
    assert "not on origin/main" in result.stderr
    assert git(origin, "tag") == ""


def test_release_refuses_a_tree_the_pre_release_run_did_not_pass(release_repo):
    work, origin, run = release_repo
    (work / ".git" / "pre_release_qa.ok").write_text("a tree of an older run\n")

    result = run("patch")

    assert result.returncode == 1
    assert "no green pre-release run for this tree" in result.stderr
    assert git(origin, "tag") == ""


def test_a_hotfix_may_skip_the_pre_release_run_and_says_so(release_repo):
    work, origin, run = release_repo
    (work / ".git" / "pre_release_qa.ok").unlink()

    result = run("patch", SKIP_PRERELEASE_QA="1")

    assert result.returncode == 0, result.stderr
    assert "SKIP_PRERELEASE_QA=1: releasing without the pre-release run" in result.stderr
    assert git(origin, "tag").strip() == "v1.2.4"


def test_release_refuses_an_existing_tag(release_repo):
    work, _, run = release_repo
    git(work, "tag", "v1.2.4")

    result = run("patch")

    assert result.returncode == 1
    assert "v1.2.4 already exists" in result.stderr
    assert git(work, "status", "--porcelain") == ""
