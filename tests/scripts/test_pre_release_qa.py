"""scripts/pre_release_qa.sh stamps a tree only when every stage passed, and only a clean one."""

from tests.script_fixtures import git

_MONGO = "evlampiy-qa-mongo-<pid>"
_MUTMUT = (
    "TEST_MONGO_URI=mongodb://127.0.0.1:27999/ systemd-run --user --scope --quiet -p MemoryMax=2200M"
    " -p MemorySwapMax=0 -p OOMPolicy=continue uv run mutmut run --max-children 2"
)
QA_STAGES = [
    "gate.sh",
    "uv run python scripts/crap.py coverage.json --max 20",
    "stack_smoke.sh",
    f"docker run -d --rm --name {_MONGO} -p 127.0.0.1::27017 --memory 512m"
    " --memory-swap 512m --ulimit nofile=64000:64000 mongo:8.0.3 --wiredTigerCacheSizeGB 0.25",
    f"docker exec {_MONGO} mongosh --quiet --eval db.runCommand({{ping: 1}}).ok",
    f"docker port {_MONGO} 27017",
    _MUTMUT,
    "uv run mutmut export-cicd-stats",
    "uv run python scripts/mutation_ratchet.py mutants/mutmut-cicd-stats.json --survived-max 195 --no-tests-max 49",
    f"docker stop {_MONGO}",
]


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


def test_the_mutants_mongodb_is_stopped_when_the_mutation_run_fails(run_qa):
    _, run = run_qa

    result, commands, stamp = run(fail=_MUTMUT.removeprefix("TEST_MONGO_URI=mongodb://127.0.0.1:27999/ "))

    assert result.returncode != 0
    assert commands[-2:] == [_MUTMUT, f"docker stop {_MONGO}"]
    assert stamp is None


def test_a_worker_count_that_is_not_a_whole_number_is_refused_before_the_container(run_qa):
    _, run = run_qa

    result, commands, _ = run(MUTMUT_CHILDREN="two")

    assert result.returncode == 1
    assert "MUTMUT_CHILDREN must be a positive whole number, not 'two'" in result.stderr
    assert not any(command.startswith("docker run") for command in commands)


def test_a_dirty_tree_is_refused_before_any_stage(run_qa):
    tree, run = run_qa
    (tree / "notes.txt").write_text("uncommitted\n")

    result, commands, stamp = run()

    assert result.returncode == 1
    assert "the tree is dirty" in result.stderr
    assert (commands, stamp) == ([], None)
