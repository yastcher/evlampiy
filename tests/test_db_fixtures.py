"""The test database a session holds: never one another session holds, kept rather than dropped."""

import pymongo

from evlampiy.dto import UserSettings
from tests.db_fixtures import bind_models, held_database


def test_two_sessions_at_once_hold_two_databases(mongo_uri, database_prefix):
    with held_database(mongo_uri, database_prefix) as first, held_database(mongo_uri, database_prefix) as second:
        assert (first, second) == (f"{database_prefix}_0", f"{database_prefix}_1")


def test_a_database_let_go_is_held_again_with_its_collections(mongo_uri, database_prefix):
    """Dropped per mutant session, the databases queued more removals than mongod finished, and it ran out of memory."""
    with held_database(mongo_uri, database_prefix) as first, pymongo.MongoClient(mongo_uri) as client:
        client[first]["notes"].insert_one({"left": "behind"})

    with held_database(mongo_uri, database_prefix) as again, pymongo.MongoClient(mongo_uri) as client:
        assert (again, client[again].list_collection_names()) == (first, ["notes"])


def test_what_an_earlier_session_left_is_emptied(mongo_uri, database_prefix):
    """A session mutmut killed mid-test leaves its documents behind."""
    with held_database(mongo_uri, database_prefix) as first, pymongo.MongoClient(mongo_uri) as client:
        client[first]["notes"].insert_many([{"left": "behind"}, {"left": "too"}])

    with held_database(mongo_uri, database_prefix) as again, pymongo.MongoClient(mongo_uri) as client:
        assert client[again]["notes"].count_documents({}) == 0


async def test_an_index_the_models_no_longer_declare_does_not_outlive_them():
    """The session's database is kept for the next session, and a stale unique index would refuse its inserts."""
    collection = UserSettings.get_pymongo_collection()
    await collection.create_index("gone", name="gone_1", unique=True)

    await bind_models(collection.database)

    assert "gone_1" not in await collection.index_information()
