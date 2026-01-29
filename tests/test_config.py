from src.config import _parse_comma_separated_ids


class TestParseCommaSeparatedIds:
    def test_empty_string(self):
        assert _parse_comma_separated_ids("") == set()

    def test_whitespace_only(self):
        assert _parse_comma_separated_ids("   ") == set()

    def test_single_id(self):
        assert _parse_comma_separated_ids("123") == {123}

    def test_multiple_ids(self):
        assert _parse_comma_separated_ids("123,456,789") == {123, 456, 789}

    def test_whitespace_around_ids(self):
        assert _parse_comma_separated_ids(" 123 , 456 ") == {123, 456}

    def test_empty_segments_ignored(self):
        assert _parse_comma_separated_ids("123,,456,") == {123, 456}
