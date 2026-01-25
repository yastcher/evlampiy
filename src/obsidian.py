import base64
import datetime
import logging

import requests

from telegram import Update

from src.chat_params import get_chat_id
from src.mongo import get_github_settings

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
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in (200, 201):
        logger.debug(f"Created note {filename} in the repository.")
    else:
        logger.error(
            f"Error creating note. Status: {response.status_code}, Details: {response.json()}"
        )
