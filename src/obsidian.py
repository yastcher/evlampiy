import datetime
import logging

from src.github_api import OBSIDIAN_NOTES_FOLDER, put_github_file
from src.mongo import get_github_settings, get_save_to_obsidian

logger = logging.getLogger(__name__)


async def add_short_note_to_obsidian(chat_id: str, text: str) -> bool:
    """
    Creates a short note in the GitHub repository's `income` folder.
    """
    if not text:
        return False

    github_settings = await get_github_settings(chat_id)
    if not github_settings:
        logger.warning("GitHub settings not found for chat %s", chat_id)
        return False

    now_str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"income/{now_str}.md"
    commit_message = f"Add short note {now_str}"

    result = await put_github_file(
        token=github_settings["token"],
        owner=github_settings["owner"],
        repo=github_settings["repo"],
        path=filename,
        content=text,
        commit_message=commit_message,
    )

    if result:
        logger.debug("Created note %s in the repository.", filename)
    else:
        logger.error("Error creating note %s", filename)

    return result


async def save_transcription_to_obsidian(
    chat_id: str,
    text: str,
    source: str,
    language: str,
    settings_chat_id: str | None = None,
    original_text: str | None = None,
) -> tuple[bool, str | None]:
    """
    Save transcription to Obsidian vault via GitHub.

    If original_text is provided and differs from text, appends an HTML comment block
    with the raw transcription so both versions are preserved in the note.

    Returns:
        tuple[bool, str | None]: (success, filename) where filename is just the name without path
    """
    lookup_id = settings_chat_id or chat_id
    if not await get_save_to_obsidian(lookup_id):
        return False, None

    github_settings = await get_github_settings(lookup_id)
    if not github_settings:
        return False, None

    now = datetime.datetime.now(datetime.UTC)
    now_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{now_str}.md"
    filepath = f"{OBSIDIAN_NOTES_FOLDER}/{filename}"

    frontmatter = (
        "---\n"
        f"date: {now.isoformat()}Z\n"
        f"source: {source}\n"
        f"language: {language}\n"
        f"chat_id: {chat_id}\n"
        "---\n\n"
    )
    content = frontmatter + text
    if original_text and original_text != text:
        content += f"\n\n<!-- original\n{original_text}\n-->"

    result = await put_github_file(
        token=github_settings["token"],
        owner=github_settings["owner"],
        repo=github_settings["repo"],
        path=filepath,
        content=content,
        commit_message=f"Add transcription {now_str}",
    )

    if result:
        logger.info("Saved transcription to %s for %s", filepath, chat_id)
    else:
        logger.error("Failed to save transcription for %s", chat_id)

    return result, filename if result else None
