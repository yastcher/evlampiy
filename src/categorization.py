"""Note categorization using AI providers."""

import json
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

_VOCABULARY_PATH = "vocabulary.json"
_VOCABULARY_MAX_KEYWORDS_PER_CATEGORY = 50


async def get_existing_categories(token: str, owner: str, repo: str) -> list[str]:
    """Get list of existing category folders, excluding system folders."""
    contents = await get_repo_contents(token, owner, repo)
    categories = []
    for item in contents:
        if item.get("type") == "dir" and item["name"] not in const.EXCLUDED_CATEGORIES:
            categories.append(item["name"])
    return categories


async def get_vocabulary_from_repo(token: str, owner: str, repo: str) -> dict:
    """Read vocabulary.json from repo root. Returns {} if absent or invalid."""
    file_data = await get_github_file(token, owner, repo, _VOCABULARY_PATH)
    if not file_data:
        return {}
    content, _ = file_data
    try:
        return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        logger.warning("vocabulary.json is invalid JSON, ignoring")
        return {}


async def update_vocabulary_in_repo(
    token: str, owner: str, repo: str, category: str, keywords: list[str]
) -> None:
    """Merge new keywords into vocabulary.json, deduplicating and capping at 50 per category."""
    vocabulary = await get_vocabulary_from_repo(token, owner, repo)
    existing = vocabulary.get(category, [])
    # dict.fromkeys preserves insertion order and deduplicates
    merged = list(dict.fromkeys(existing + keywords))
    vocabulary[category] = merged[:_VOCABULARY_MAX_KEYWORDS_PER_CATEGORY]
    content = json.dumps(vocabulary, ensure_ascii=False, indent=2)
    await put_github_file(
        token=token,
        owner=owner,
        repo=repo,
        path=_VOCABULARY_PATH,
        content=content,
        commit_message=f"Update vocabulary for {category}",
    )


async def classify_note(
    text: str,
    existing_categories: list[str],
    vocabulary: dict | None = None,
) -> tuple[str | None, list[str]]:
    """Classify note text into a category using the configured AI provider.

    Returns (category, keywords) where keywords are domain terms extracted from the note.
    """
    categories_list = ", ".join(existing_categories) if existing_categories else "none"
    vocab_hint = ""
    if vocabulary:
        flat = ", ".join(kw for keywords in vocabulary.values() for kw in keywords)
        vocab_hint = f"\nDomain vocabulary: {flat}"

    prompt = (
        f"Analyze this note and return JSON only:\n"
        f'{{"category": "<name>", "keywords": ["word1", "word2"]}}\n\n'
        f"Keywords: domain-specific words/phrases from this note that characterize the category "
        f"(up to 5). These help recognize similar notes and fix transcription errors.\n\n"
        f"Rules for category:\n"
        f"1. If the note fits an existing category, return that category name exactly.\n"
        f"2. If no existing category fits, suggest a new short name "
        f"(1-2 words, lowercase, no spaces, use underscores).\n\n"
        f"Existing categories: {categories_list}"
        f"{vocab_hint}\n\n"
        f"Note:\n{text}"
    )

    result = await classify_text(prompt)
    if not result:
        return None, []

    try:
        data = json.loads(result.strip())
        raw_category = data.get("category", "").strip().lower().replace(" ", "_")
        keywords = [str(k) for k in data.get("keywords", [])[:5]]
        return raw_category or None, keywords
    except (json.JSONDecodeError, TypeError, AttributeError):
        # Fallback: treat as plain category name (old-style LLM response)
        category = result.strip().lower().replace(" ", "_")
        return category or None, []


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
    token: str,
    owner: str,
    repo: str,
    filename: str,
    content: str,
    existing_categories: list[str] | None = None,
    vocabulary: dict | None = None,
) -> str | None:
    """Categorize a single note and move it to the appropriate folder."""
    if existing_categories is None:
        existing_categories = await get_existing_categories(token, owner, repo)
    if vocabulary is None:
        vocabulary = await get_vocabulary_from_repo(token, owner, repo)

    category, keywords = await classify_note(content, existing_categories, vocabulary)
    if not category:
        return None

    old_path = f"{OBSIDIAN_NOTES_FOLDER}/{filename}"
    new_path = f"{category}/{filename}"

    success = await move_github_file(token, owner, repo, old_path, new_path)
    if success:
        logger.info("Categorized %s to %s", filename, category)
        if keywords:
            await update_vocabulary_in_repo(token, owner, repo, category, keywords)
        return category

    logger.error("Failed to move %s to %s", filename, category)
    return None


async def categorize_all_income(token: str, owner: str, repo: str) -> int:
    """Categorize all files in the income folder. Returns count of processed files."""
    existing_categories = await get_existing_categories(token, owner, repo)
    vocabulary = await get_vocabulary_from_repo(token, owner, repo)
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
        result = await categorize_note(
            token, owner, repo, item["name"], content, existing_categories, vocabulary
        )
        if result:
            processed += 1

    return processed
