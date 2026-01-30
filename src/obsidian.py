import base64
import datetime
import logging

import httpx

from telegram import Update

from src.chat_params import get_chat_id
from src.github_api import OBSIDIAN_NOTES_FOLDER, put_github_file
from src.mongo import get_github_settings, get_save_to_obsidian

logger = logging.getLogger(__name__)


async def add_short_note_to_obsidian(update: Update):
    """
    Creates a short note in the GitHub repository's `income` folder.
    """
    if not update.message or not update.message.text:
        return
    note_text = update.message.text
    now_str = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"income/{now_str}.md"
    content_base64 = base64.b64encode(note_text.encode("utf-8")).decode("utf-8")
    commit_message = f"Add short note {now_str}"
    chat_id = get_chat_id(update)
    github_settings = await get_github_settings(chat_id)
    github_repo = github_settings["owner"] + "/" + github_settings["repo"]
    github_token = github_settings["token"]
    url = f"https://api.github.com/repos/{github_repo}/contents/{filename}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }
    data = {"message": commit_message, "content": content_base64}
    async with httpx.AsyncClient() as client:
        response = await client.put(url, headers=headers, json=data)
    if response.status_code in (200, 201):
        logger.debug(f"Created note {filename} in the repository.")
    else:
        logger.error(
            f"Error creating note. Status: {response.status_code}, Details: {response.json()}"
        )


async def save_transcription_to_obsidian(
    chat_id: str,
    text: str,
    source: str,
    language: str,
) -> tuple[bool, str | None]:
    """
    Save transcription to Obsidian vault via GitHub.

    Returns:
        tuple[bool, str | None]: (success, filename) where filename is just the name without path
    """
    if not await get_save_to_obsidian(chat_id):
        return False, None

    github_settings = await get_github_settings(chat_id)
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
