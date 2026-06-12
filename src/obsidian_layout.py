"""Folder layout for the bot's working area inside the connected vault repo.

All paths are relative to ``settings.obsidian_base_dir`` (e.g. ``evlampiy``), so
the bot never touches the repo root: notes land in ``<base>/inbox`` and are moved
into ``<base>/<category>`` or ``<base>/trash``.
"""

from src import const
from src.config import settings


def base_dir() -> str:
    """Bot's working subdirectory inside the vault repo."""
    return settings.obsidian_base_dir


def inbox_dir() -> str:
    """Folder where new notes land before categorization."""
    return f"{settings.obsidian_base_dir}/{const.OBSIDIAN_INBOX_FOLDER}"


def trash_dir() -> str:
    """Folder for obvious garbage notes."""
    return f"{settings.obsidian_base_dir}/{const.OBSIDIAN_TRASH_FOLDER}"


def category_dir(category: str) -> str:
    """Folder for a given note category."""
    return f"{settings.obsidian_base_dir}/{category}"
