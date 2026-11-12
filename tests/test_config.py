from evlampiy.config import Settings, _parse_comma_separated_ids


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
