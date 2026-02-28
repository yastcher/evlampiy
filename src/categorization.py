"""Note categorization using AI providers."""

import json
import logging
from collections.abc import Mapping, Sequence

from src import const
from src.ai_client import classify_text
from src.github_api import (
    OBSIDIAN_NOTES_FOLDER,
    GitHubRepo,
    delete_github_file,
    get_github_file,
    get_repo_contents,
    put_github_file,
)
from src.prompts import CATEGORIZE_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

_VOCABULARY_PATH = "vocabulary.json"
_VOCABULARY_MAX_KEYWORDS_PER_CATEGORY = 50


async def get_existing_categories(repo_info: GitHubRepo) -> list[str]:
    """Get list of existing category folders, excluding system folders."""
    contents = await get_repo_contents(repo_info)
    categories = []
    for item in contents:
        if item.get("type") == "dir" and item["name"] not in const.EXCLUDED_CATEGORIES:
            categories.append(item["name"])
    return categories


async def get_vocabulary_from_repo(repo_info: GitHubRepo) -> dict[str, list[str]]:
    """Read vocabulary.json from repo root. Returns {} if absent or invalid."""
    file_data = await get_github_file(repo_info, _VOCABULARY_PATH)
    if not file_data:
        return {}
    content, _ = file_data
    try:
        data: dict[str, list[str]] = json.loads(content)
        return data
    except (json.JSONDecodeError, ValueError):
        logger.warning("vocabulary.json is invalid JSON, ignoring")
        return {}


async def update_vocabulary_in_repo(
    repo_info: GitHubRepo, category: str, keywords: Sequence[str]
) -> None:
    """Merge new keywords into vocabulary.json, deduplicating and capping at 50 per category."""
    vocabulary = await get_vocabulary_from_repo(repo_info)
    existing = vocabulary.get(category, [])
    # dict.fromkeys preserves insertion order and deduplicates
    merged = list(dict.fromkeys(existing + list(keywords)))
    vocabulary[category] = merged[:_VOCABULARY_MAX_KEYWORDS_PER_CATEGORY]
    content = json.dumps(vocabulary, ensure_ascii=False, indent=2)
    await put_github_file(
        repo_info=repo_info,
        path=_VOCABULARY_PATH,
        content=content,
        commit_message=f"Update vocabulary for {category}",
    )


async def classify_note(
    text: str,
    existing_categories: Sequence[str],
    vocabulary: Mapping[str, Sequence[str]] | None = None,
) -> tuple[str | None, list[str]]:
    """Classify note text into a category using the configured AI provider.

    Returns (category, keywords) where keywords are domain terms extracted from the note.
    """
    categories_list = ", ".join(existing_categories) if existing_categories else "none"
    vocab_hint = ""
    if vocabulary:
        flat = ", ".join(kw for keywords in vocabulary.values() for kw in keywords)
        vocab_hint = f"\nDomain vocabulary: {flat}"

    prompt = CATEGORIZE_PROMPT_TEMPLATE.format(
        categories_list=categories_list,
        vocab_hint=vocab_hint,
        text=text,
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


async def move_github_file(repo_info: GitHubRepo, old_path: str, new_path: str) -> bool:
    """Move a file in GitHub by copying content and deleting original."""
    file_data = await get_github_file(repo_info, old_path)
    if not file_data:
        return False

    content, sha = file_data

    success = await put_github_file(
        repo_info=repo_info,
        path=new_path,
        content=content,
        commit_message=f"Move {old_path} to {new_path}",
    )
    if not success:
        return False

    await delete_github_file(
        repo_info=repo_info,
        path=old_path,
        sha=sha,
        commit_message=f"Delete original {old_path}",
    )
    return True


async def categorize_note(
    repo_info: GitHubRepo,
    filename: str,
    content: str,
    existing_categories: Sequence[str] | None = None,
    vocabulary: Mapping[str, Sequence[str]] | None = None,
) -> str | None:
    """Categorize a single note and move it to the appropriate folder."""
    if existing_categories is None:
        existing_categories = await get_existing_categories(repo_info)
    if vocabulary is None:
        vocabulary = await get_vocabulary_from_repo(repo_info)

    category, keywords = await classify_note(content, existing_categories, vocabulary)
    if not category:
        return None

    old_path = f"{OBSIDIAN_NOTES_FOLDER}/{filename}"
    new_path = f"{category}/{filename}"

    success = await move_github_file(repo_info, old_path, new_path)
    if success:
        logger.info("Categorized %s to %s", filename, category)
        if keywords:
            await update_vocabulary_in_repo(repo_info, category, keywords)
        return category

    logger.error("Failed to move %s to %s", filename, category)
    return None


async def categorize_all_income(repo_info: GitHubRepo) -> int:
    """Categorize all files in the income folder. Returns count of processed files."""
    existing_categories = await get_existing_categories(repo_info)
    vocabulary = await get_vocabulary_from_repo(repo_info)
    contents = await get_repo_contents(repo_info, OBSIDIAN_NOTES_FOLDER)
    processed = 0

    for item in contents:
        if item.get("type") != "file" or not item["name"].endswith(".md"):
            continue
        if item["name"] == ".gitkeep":
            continue

        file_data = await get_github_file(repo_info, f"{OBSIDIAN_NOTES_FOLDER}/{item['name']}")
        if not file_data:
            continue

        content, _ = file_data
        result = await categorize_note(
            repo_info, item["name"], content, existing_categories, vocabulary
        )
        if result:
            processed += 1

    return processed
