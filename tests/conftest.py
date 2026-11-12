from evlampiy import config
from tests.settings_isolation import isolated_settings

# Before the fixture modules below import the app: each module keeps the `settings` it found.
config.settings = isolated_settings()

pytest_plugins = [
    "tests.fixtures",
    "tests.db_fixtures",
    "tests.script_fixtures",
]
