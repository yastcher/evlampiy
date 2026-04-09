"""Tool definitions and implementations for GPT tool calling."""

import dataclasses
import functools
import json
import logging
import typing

from src.categorization import get_existing_categories
from src.mongo import (
    get_auto_categorize,
    get_auto_cleanup,
    get_chat_language,
    get_github_settings,
    get_recent_transcriptions,
    get_save_to_obsidian,
)
from src.types import ChatId

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class ToolDef:
    """A tool the LLM can call during a conversation."""

    name: str
    description: str
    parameters: dict[str, typing.Any]  # JSON Schema for function parameters
    handler: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, str]]


# ---------------------------------------------------------------------------
# Tool implementations — each returns a string for the LLM
# ---------------------------------------------------------------------------


async def _get_recent_notes(chat_id: ChatId, limit: int = 3) -> str:
    """Return recent voice transcriptions as a JSON list."""
    notes = await get_recent_transcriptions(chat_id, limit=limit)
    if not notes:
        return json.dumps({"notes": [], "message": "No recent notes found"})
    return json.dumps({"notes": notes, "count": len(notes)}, ensure_ascii=False)


async def _get_user_settings(chat_id: ChatId) -> str:
    """Return current user settings as JSON."""
    language = await get_chat_language(chat_id)
    save_obsidian = await get_save_to_obsidian(chat_id)
    auto_cat = await get_auto_categorize(chat_id)
    auto_clean = await get_auto_cleanup(chat_id)
    repo = await get_github_settings(chat_id)

    result = {
        "language": language,
        "save_to_obsidian": save_obsidian,
        "auto_categorize": auto_cat,
        "auto_cleanup": auto_clean,
        "obsidian_connected": repo is not None,
    }
    return json.dumps(result, ensure_ascii=False)


async def _get_categories(chat_id: ChatId) -> str:
    """Return list of note categories from the user's Obsidian repository."""
    repo = await get_github_settings(chat_id)
    if repo is None:
        return json.dumps({"categories": [], "message": "Obsidian repository not connected"})

    try:
        categories = await get_existing_categories(repo)
    except Exception:
        logger.exception("Failed to fetch categories for chat %s", chat_id)
        return json.dumps({"categories": [], "message": "Failed to fetch categories"})

    return json.dumps({"categories": categories, "count": len(categories)}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

_TOOL_DEFS: list[
    tuple[
        str,
        str,
        dict[str, typing.Any],
        typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, str]],
    ]
] = [
    (
        "get_recent_notes",
        "Get recent voice transcription notes from this chat",
        {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of notes to return (default 3)",
                },
            },
            "required": [],
        },
        _get_recent_notes,
    ),
    (
        "get_user_settings",
        "Get the user's current bot settings"
        " (language, obsidian sync, auto-categorize, auto-cleanup)",
        {"type": "object", "properties": {}, "required": []},
        _get_user_settings,
    ),
    (
        "get_categories",
        "Get list of note categories from the user's Obsidian repository",
        {"type": "object", "properties": {}, "required": []},
        _get_categories,
    ),
]


def get_tools(chat_id: ChatId) -> list[ToolDef]:
    """Return tools available for a given chat, with chat_id bound into handlers."""
    tools = []
    for name, description, parameters, handler in _TOOL_DEFS:
        bound = functools.partial(handler, chat_id)
        tools.append(
            ToolDef(
                name=name,
                description=description,
                parameters=parameters,
                handler=bound,
            )
        )
    return tools
