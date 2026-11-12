"""scripts/pre_release_qa.sh stamps a tree only when every stage passed, and only a clean one."""

from tests.script_fixtures import git

QA_STAGES = ["gate.sh", "uv run python scripts/crap.py coverage.json --max 20"]


def test_a_green_run_stamps_the_tree_it_checked(run_qa):
    tree, run = run_qa

    result, commands, stamp = run()

    assert result.returncode == 0, result.stderr
    assert commands == QA_STAGES
    assert stamp == git(tree, "rev-parse", "HEAD^{tree}").strip()


def test_a_failed_stage_stops_the_run_and_takes_the_earlier_stamp_with_it(run_qa):
    _, run = run_qa
    run()

    result, commands, stamp = run(fail="gate.sh ")

    assert result.returncode != 0
    assert commands == ["gate.sh"]
    assert stamp is None


def test_a_dirty_tree_is_refused_before_any_stage(run_qa):
    tree, run = run_qa
    (tree / "notes.txt").write_text("uncommitted\n")

    result, commands, stamp = run()

    assert result.returncode == 1
    assert "the tree is dirty" in result.stderr
    assert (commands, stamp) == ([], None)
