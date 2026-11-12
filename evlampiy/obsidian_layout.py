"""Folder layout for the bot's working area inside the connected vault repo.

All paths are relative to ``settings.obsidian_base_dir`` (e.g. ``evlampiy``): notes land
in ``<base>/inbox`` and are moved into ``<base>/<category>`` or ``<base>/trash``. At the
repo root the bot writes only ``vocabulary.json`` (categorization) and the obsidian-git
plugin's ``data.json``.
"""

from evlampiy import const
from evlampiy.config import settings


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
