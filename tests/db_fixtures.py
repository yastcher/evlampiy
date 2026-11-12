"""The tests' MongoDB: one server per session, a clean database per test."""

import os
import pathlib
import re
from collections.abc import Iterator

import pymongo
import docker.types
import pytest
from beanie import init_beanie
from docker.errors import DockerException
from pymongo import AsyncMongoClient
from testcontainers.community.mongodb import MongoDbContainer

from evlampiy.mongo import ALL_DOCUMENT_MODELS

# The tests' own database: TEST_MONGO_URI may point at a server that holds other data,
# and every test empties the collections it used.
_TEST_DATABASE = "evlampiy_test"

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
        with pymongo.MongoClient(uri) as client:
            client.drop_database(_TEST_DATABASE)
        yield uri
        return
    try:
        # The client reaches for the Docker daemon as soon as the container is built.
        container = (
            MongoDbContainer(compose_mongo_image(_PRODUCTION_COMPOSE))
            .with_command(f"--wiredTigerCacheSizeGB {_MONGO_CACHE_GB}")
            .with_kwargs(mem_limit=_MONGO_MEMORY_LIMIT, ulimits=[_MONGO_OPEN_FILES])
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


@pytest.fixture(autouse=True)
async def init_db(mongo_uri):
    """Bind the app's models to the test database; empty their collections after the test."""
    client = AsyncMongoClient(mongo_uri)
    await init_beanie(database=client[_TEST_DATABASE], document_models=ALL_DOCUMENT_MODELS)
    yield
    for model in ALL_DOCUMENT_MODELS:
        await model.delete_all()
    await client.close()
