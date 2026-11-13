"""The tests' MongoDB: one server per session, a clean database per test."""

import contextlib
import fcntl
import itertools
import os
import pathlib
import re
import tempfile
import uuid
from collections.abc import Generator, Iterator

import docker.types
import pymongo
import pytest
from beanie import init_beanie
from docker.errors import DockerException
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from testcontainers.community.mongodb import MongoDbContainer

from evlampiy.mongo import ALL_DOCUMENT_MODELS

# A small fixed cache and a hard memory limit: on a laptop the test mongod shares the memory
# with the IDE, and by default it sizes its cache by the whole machine.
_MONGO_CACHE_GB = "0.25"
_MONGO_MEMORY_LIMIT = "512m"
# Docker gives a container 1024 open files; WiredTiger keeps one per collection and index,
# and at the limit mongod aborts (EMFILE). 64000 is what MongoDB asks for.
_MONGO_OPEN_FILES = docker.types.Ulimit(name="nofile", soft=64000, hard=64000)
# The image starts mongod twice — the first one creates the user — and the container counts
# as started at the first: the first ping waits this long for the server that stays.
_MONGO_START_TIMEOUT_MS = 60_000


_PRODUCTION_COMPOSE = pathlib.Path(__file__).resolve().parents[1] / "docker-compose.yml"
# Where the sessions on this machine agree which test database each holds.
_DATABASE_LOCKS = pathlib.Path(tempfile.gettempdir())


def compose_mongo_image(compose: pathlib.Path) -> str:
    """The image the `mongodb` service of a docker-compose file runs."""
    service = re.search(r"^  mongodb:\n(?:    .*\n)*?    image: (\S+)$", compose.read_text(), re.M)
    assert service is not None, f"{compose} runs no mongodb image"
    return service[1]


@pytest.fixture(scope="session")
def mongo_uri() -> Iterator[str]:
    """The session's MongoDB — never MONGO_URI, which is the app's own database.

    TEST_MONGO_URI when set (CI's service container); otherwise a container of the image
    production runs, started for the session, so a local run needs Docker.
    """
    if uri := os.environ.get("TEST_MONGO_URI"):
        yield uri
        return
    try:
        # The client reaches for the Docker daemon as soon as the container is built.
        container = (
            MongoDbContainer(compose_mongo_image(_PRODUCTION_COMPOSE))
            .with_command(f"--wiredTigerCacheSizeGB {_MONGO_CACHE_GB}")
            .with_kwargs(mem_limit=_MONGO_MEMORY_LIMIT, memswap_limit=_MONGO_MEMORY_LIMIT, ulimits=[_MONGO_OPEN_FILES])
        )
        container.start()
    except DockerException as error:
        pytest.exit(
            f"The tests need MongoDB: start Docker, or point TEST_MONGO_URI at a server ({error})",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )
    try:
        uri = container.get_connection_url()
        with pymongo.MongoClient(uri, serverSelectionTimeoutMS=_MONGO_START_TIMEOUT_MS) as client:
            client.admin.command("ping")
        yield uri
    finally:
        container.stop()


@contextlib.contextmanager
def held_database(mongo_uri: str, prefix: str) -> Generator[str]:
    """The first `<prefix>_<n>` database no other session holds, emptied of what an earlier one left.

    mutmut runs a test session per mutant, two at once, on the one server pre-release QA starts.
    A database created and dropped per session queued its collections and indexes for removal
    faster than mongod removed them, and their memory took mongod past its cap (2026-11-12). So
    a database is kept for the next session, and a lock on its file, which the system lets go
    even when the session is killed, keeps two sessions at once out of one database.
    """
    for slot in itertools.count():
        with (_DATABASE_LOCKS / f"{prefix}-{slot}.lock").open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            name = f"{prefix}_{slot}"
            with pymongo.MongoClient(mongo_uri) as client:
                for collection in client[name].list_collection_names():
                    client[name][collection].delete_many({})
            yield name
            return


@pytest.fixture(scope="session")
def test_database(mongo_uri) -> Iterator[str]:
    """This session's database: one no other session holds, TEST_MONGO_URI's server may hold other data."""
    with held_database(mongo_uri, "evlampiy_test") as name:
        yield name


@pytest.fixture
def database_prefix(mongo_uri) -> Iterator[str]:
    """A prefix of `held_database` databases of the test's own, dropped after it with their locks."""
    prefix = f"held_{uuid.uuid4().hex[:8]}"
    yield prefix
    with pymongo.MongoClient(mongo_uri) as client:
        for name in client.list_database_names():
            if name.startswith(f"{prefix}_"):
                client.drop_database(name)
    for lock in _DATABASE_LOCKS.glob(f"{prefix}-*.lock"):
        lock.unlink()


async def bind_models(database: AsyncDatabase) -> None:
    """Bind the app's models to a test database. It outlives the session (`held_database`), so an
    index the models no longer declare is dropped rather than left to refuse inserts."""
    await init_beanie(database=database, document_models=ALL_DOCUMENT_MODELS, allow_index_dropping=True)


@pytest.fixture(autouse=True)
async def init_db(mongo_uri, test_database):
    """Bind the app's models to the session's database; empty their collections after the test."""
    client = AsyncMongoClient(mongo_uri)
    await bind_models(client[test_database])
    yield
    for model in ALL_DOCUMENT_MODELS:
        await model.delete_all()
    await client.close()
