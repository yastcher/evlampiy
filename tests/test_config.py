import sys

from evlampiy.config import Settings, _parse_comma_separated_ids
from tests.settings_isolation import isolated_settings


class TestTestSessionSettings:
    def test_the_app_runs_on_the_isolated_settings(self):
        """conftest swaps the settings before importing the app: a module holding older ones keeps the developer's."""
        holders = {
            name: module.settings
            for name, module in list(sys.modules.items())
            if name.startswith("evlampiy.") and isinstance(getattr(module, "settings", None), Settings)
        }

        assert "evlampiy.ai_client" in holders
        stale = {name: held.environment for name, held in holders.items() if held.environment != "test"}
        assert stale == {}

    def test_isolated_settings_read_neither_the_dotenv_nor_the_shell(self, tmp_path, monkeypatch):
        """Where the developer's .env and shell hold keys, a test session's settings hold none."""
        (tmp_path / ".env").write_text("GROQ_API_KEY=from-dotenv\nMONGO_URI=mongodb://prod:27017/\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("OPENROUTER_API_KEY", "from-shell")

        settings = isolated_settings()

        assert (settings.groq_api_key, settings.openrouter_api_key, settings.mongo_uri) == (
            "",
            "",
            "mongodb://mongodb:27017/",
        )


class TestSettingsExtraEnv:
    def test_unknown_dotenv_keys_are_ignored(self, tmp_path):
        """.env is shared with deploy tooling (CLOUDFLARE_*); keys the app does not declare must not crash it."""
        dotenv = tmp_path / ".env"
        dotenv.write_text("CLOUDFLARE_ACCOUNT_ID=x\nCLOUDFLARE_API_TOKEN=y\n")

        settings = Settings(_env_file=dotenv)

        assert not hasattr(settings, "cloudflare_account_id")


class TestParseCommaSeparatedIds:
    def test_empty_string(self):
        assert _parse_comma_separated_ids("") == set()

    def test_whitespace_only(self):
        assert _parse_comma_separated_ids("   ") == set()

    def test_single_id(self):
        assert _parse_comma_separated_ids("123") == {"123"}

    def test_multiple_ids(self):
        assert _parse_comma_separated_ids("123,456,789") == {"123", "456", "789"}

    def test_whitespace_around_ids(self):
        assert _parse_comma_separated_ids(" 123 , 456 ") == {"123", "456"}

    def test_empty_segments_ignored(self):
        assert _parse_comma_separated_ids("123,,456,") == {"123", "456"}
