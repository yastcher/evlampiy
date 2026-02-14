"""Note categorization using AI providers."""

import asyncio
import logging

from src import const
from src.ai_client import classify_text
from src.github_api import (
    OBSIDIAN_NOTES_FOLDER,
    delete_github_file,
    get_github_file,
    get_repo_contents,
    put_github_file,
)

logger = logging.getLogger(__name__)


async def get_existing_categories(token: str, owner: str, repo: str) -> list[str]:
    """Get list of existing category folders, excluding system folders."""
    contents = await get_repo_contents(token, owner, repo)
    categories = []
    for item in contents:
        if item.get("type") == "dir" and item["name"] not in const.EXCLUDED_CATEGORIES:
            categories.append(item["name"])
    return categories


async def classify_note(text: str, existing_categories: list[str]) -> str | None:
    """Classify note text into a category using the configured AI provider."""
    categories_list = ", ".join(existing_categories) if existing_categories else "none"
    prompt = (
        f"You are a note categorizer. Analyze this note and suggest a category.\n\n"
        f"Existing categories: {categories_list}\n\n"
        f"Note text:\n{text}\n\n"
        f"Rules:\n"
        f"1. If the note fits an existing category, return that category name exactly.\n"
        f"2. If no existing category fits, suggest a new short category name "
        f"(1-2 words, lowercase, no spaces, use underscores).\n"
        f"3. Return ONLY the category name, nothing else."
    )

    result = await classify_text(prompt)
    if not result:
        return None

    category = result.strip().lower().replace(" ", "_")
    return category


async def move_github_file(token: str, owner: str, repo: str, old_path: str, new_path: str) -> bool:
    """Move a file in GitHub by copying content and deleting original."""
    file_data = await get_github_file(token, owner, repo, old_path)
    if not file_data:
        return False

    content, sha = file_data

    success = await put_github_file(
        token=token,
        owner=owner,
        repo=repo,
        path=new_path,
        content=content,
        commit_message=f"Move {old_path} to {new_path}",
    )
    if not success:
        return False

    await delete_github_file(
        token=token,
        owner=owner,
        repo=repo,
        path=old_path,
        sha=sha,
        commit_message=f"Delete original {old_path}",
    )
    return True


async def categorize_note(
    token: str, owner: str, repo: str, filename: str, content: str
) -> str | None:
    """Categorize a single note and move it to the appropriate folder."""
    existing_categories = await get_existing_categories(token, owner, repo)
    category = await classify_note(content, existing_categories)
    if not category:
        return None

    old_path = f"{OBSIDIAN_NOTES_FOLDER}/{filename}"
    new_path = f"{category}/{filename}"

    success = await move_github_file(token, owner, repo, old_path, new_path)
    if success:
        logger.info("Categorized %s to %s", filename, category)
        return category

    logger.error("Failed to move %s to %s", filename, category)
    return None


async def categorize_all_income(token: str, owner: str, repo: str) -> int:
    """Categorize all files in the income folder. Returns count of processed files."""
    contents = await get_repo_contents(token, owner, repo, OBSIDIAN_NOTES_FOLDER)
    processed = 0

    for item in contents:
        if item.get("type") != "file" or not item["name"].endswith(".md"):
            continue
        if item["name"] == ".gitkeep":
            continue

        file_data = await get_github_file(
            token, owner, repo, f"{OBSIDIAN_NOTES_FOLDER}/{item['name']}"
        )
        if not file_data:
            continue

        content, _ = file_data
        result = await categorize_note(token, owner, repo, item["name"], content)
        if result:
            processed += 1
        await asyncio.sleep(4)  # 15 RPM free tier

    return processed
