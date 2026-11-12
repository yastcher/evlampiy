"""scripts/pre_release_qa.sh stamps a tree only when every stage passed, and only a clean one."""

import pytest

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
    "free -m",
    f"docker run -d --rm --name {_MONGO} -p 127.0.0.1::27017 --memory 512m"
    " --memory-swap 512m --ulimit nofile=64000:64000 mongo:8.0.3 --wiredTigerCacheSizeGB 0.25",
    f"docker exec {_MONGO} mongosh --quiet --eval db.runCommand({{ping: 1}}).ok",
    f"docker port {_MONGO} 27017",
    _MUTMUT,
    "uv run mutmut results --all true",
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


_RERUN = (
    "TEST_MONGO_URI=mongodb://127.0.0.1:27999/ systemd-run --user --scope --quiet -p MemoryMax=1700M"
    " -p MemorySwapMax=0 -p OOMPolicy=continue uv run mutmut run --max-children 1"
)
_DIED_BESIDE_OTHERS = (
    "    evlampiy.a.x_f__mutmut_1: segfault\\n"
    "    evlampiy.b.x_g__mutmut_2: survived\\n"
    "    evlampiy.c.x_h__mutmut_3: timeout\\n"
)


def test_mutants_that_died_or_timed_out_beside_others_run_again_alone(run_qa):
    """The cap kills the largest process, not always the mutant that allocated: a survivor must not hide."""
    tree, run = run_qa

    result, commands, stamp = run(QA_MUTMUT_RESULTS=_DIED_BESIDE_OTHERS)

    assert result.returncode == 0, result.stderr
    after_results = commands[commands.index("uv run mutmut results --all true") + 1 :]
    assert after_results[:2] == ["free -m", f"{_RERUN} evlampiy.a.x_f__mutmut_1 evlampiy.c.x_h__mutmut_3"]
    assert stamp == git(tree, "rev-parse", "HEAD^{tree}").strip()


def test_with_nothing_dead_nothing_runs_again(run_qa):
    _, run = run_qa

    _, commands, _ = run(QA_MUTMUT_RESULTS="    evlampiy.b.x_g__mutmut_2: survived\\n")

    assert not any(command.startswith(_RERUN) for command in commands)


@pytest.mark.parametrize(
    ("available_mb", "workers"),
    [(2711, 1), (2712, 2), (2212, 1), (8000, 2)],
    ids=["one-short-of-two", "two-exactly", "one-exactly", "two-at-most"],
)
def test_the_workers_are_as_many_as_the_memory_available_fits(run_qa, available_mb, workers):
    """mutmut and its fork server take 1.2 GB, each worker 0.5 GB, the MongoDB 0.5 GB."""
    _, run = run_qa

    _, commands, _ = run(QA_AVAILABLE_MB=str(available_mb))

    cap = 1200 + 500 * workers
    assert (
        f"-p MemoryMax={cap}M -p MemorySwapMax=0 -p OOMPolicy=continue uv run mutmut run --max-children {workers}"
        in ("\\n".join(commands))
    )


def test_a_run_the_memory_available_does_not_fit_does_not_start(run_qa):
    """A cap above the memory available protects nothing: the kernel would kill the desktop first."""
    _, run = run_qa

    result, commands, stamp = run(QA_AVAILABLE_MB="2211")

    assert result.returncode == 1
    assert "the memory available fits no mutation worker" in result.stderr
    assert not any(command.startswith("docker run") for command in commands)
    assert stamp is None


def test_more_workers_than_the_memory_fits_are_refused(run_qa):
    _, run = run_qa

    result, commands, _ = run(MUTMUT_CHILDREN="2", QA_AVAILABLE_MB="2300")

    assert result.returncode == 1
    assert "the memory available fits only 1 of the 2 mutation workers asked for" in result.stderr
    assert not any(command.startswith("docker run") for command in commands)


def test_the_run_again_alone_needs_its_memory_too(run_qa):
    """Memory taken while the main run went on: the run again does not start, and the MongoDB stops."""
    _, run = run_qa

    result, commands, stamp = run(QA_MUTMUT_RESULTS=_DIED_BESIDE_OTHERS, QA_AVAILABLE_AFTER_RUN_MB="2000")

    assert result.returncode == 1
    assert "2 mutants to run again alone, and the memory available fits no worker" in result.stderr
    assert not any(command.startswith(_RERUN) for command in commands)
    assert commands[-1] == f"docker stop {_MONGO}"
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
