from unittest.mock import patch

from src import obsidian_layout


def test_default_layout():
    assert obsidian_layout.base_dir() == "evlampiy"
    assert obsidian_layout.inbox_dir() == "evlampiy/inbox"
    assert obsidian_layout.trash_dir() == "evlampiy/trash"
    assert obsidian_layout.category_dir("work") == "evlampiy/work"


def test_respects_configured_base_dir():
    with patch.object(obsidian_layout.settings, "obsidian_base_dir", "myvault"):
        assert obsidian_layout.base_dir() == "myvault"
        assert obsidian_layout.inbox_dir() == "myvault/inbox"
        assert obsidian_layout.trash_dir() == "myvault/trash"
        assert obsidian_layout.category_dir("work") == "myvault/work"
