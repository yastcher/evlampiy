"""Tests for GPT tool definitions and implementations."""

import json
from unittest.mock import AsyncMock, patch

from src.mongo import (
    save_recent_transcription,
    set_auto_categorize,
    set_auto_cleanup,
    set_chat_language,
    set_save_to_obsidian,
)
from src.tools import ToolDef, get_tools

CHAT_ID = "u_12345"


class TestGetTools:
    """Test tool registry."""

    def test_returns_list_of_tool_defs(self):
        tools = get_tools(CHAT_ID)
        assert len(tools) == 3
        assert all(isinstance(t, ToolDef) for t in tools)

    def test_tool_names(self):
        tools = get_tools(CHAT_ID)
        names = [t.name for t in tools]
        assert "get_recent_notes" in names
        assert "get_user_settings" in names
        assert "get_categories" in names

    def test_handlers_are_callable(self):
        tools = get_tools(CHAT_ID)
        for tool in tools:
            assert callable(tool.handler)

    def test_parameters_have_json_schema_structure(self):
        tools = get_tools(CHAT_ID)
        for tool in tools:
            assert tool.parameters["type"] == "object"
            assert "properties" in tool.parameters


class TestGetRecentNotesTool:
    """Test get_recent_notes tool implementation."""

    async def test_returns_empty_when_no_notes(self):
        tools = get_tools(CHAT_ID)
        tool = next(t for t in tools if t.name == "get_recent_notes")

        result = json.loads(await tool.handler())
        assert result["notes"] == []
        assert "message" in result

    async def test_returns_transcriptions(self):
        await save_recent_transcription(CHAT_ID, "First note")
        await save_recent_transcription(CHAT_ID, "Second note")

        tools = get_tools(CHAT_ID)
        tool = next(t for t in tools if t.name == "get_recent_notes")

        result = json.loads(await tool.handler())
        assert result["count"] == 2
        assert "First note" in result["notes"]
        assert "Second note" in result["notes"]

    async def test_respects_limit(self):
        for i in range(5):
            await save_recent_transcription(CHAT_ID, f"Note {i}")

        tools = get_tools(CHAT_ID)
        tool = next(t for t in tools if t.name == "get_recent_notes")

        result = json.loads(await tool.handler(limit=2))
        assert result["count"] == 2

    async def test_isolates_by_chat_id(self):
        await save_recent_transcription("u_111", "Chat 1 note")
        await save_recent_transcription("u_222", "Chat 2 note")

        tools = get_tools("u_111")
        tool = next(t for t in tools if t.name == "get_recent_notes")

        result = json.loads(await tool.handler())
        assert result["count"] == 1
        assert result["notes"] == ["Chat 1 note"]


class TestGetUserSettingsTool:
    """Test get_user_settings tool implementation."""

    async def test_returns_defaults_for_new_user(self):
        tools = get_tools(CHAT_ID)
        tool = next(t for t in tools if t.name == "get_user_settings")

        result = json.loads(await tool.handler())
        assert result["save_to_obsidian"] is False
        assert result["auto_categorize"] is False
        assert result["auto_cleanup"] is False
        assert result["obsidian_connected"] is False

    async def test_returns_configured_settings(self):
        await set_chat_language(CHAT_ID, "en")
        await set_save_to_obsidian(CHAT_ID, True)
        await set_auto_categorize(CHAT_ID, True)
        await set_auto_cleanup(CHAT_ID, True)

        tools = get_tools(CHAT_ID)
        tool = next(t for t in tools if t.name == "get_user_settings")

        result = json.loads(await tool.handler())
        assert result["language"] == "en"
        assert result["save_to_obsidian"] is True
        assert result["auto_categorize"] is True
        assert result["auto_cleanup"] is True


class TestGetCategoriesTool:
    """Test get_categories tool implementation."""

    async def test_returns_message_when_no_repo(self):
        tools = get_tools(CHAT_ID)
        tool = next(t for t in tools if t.name == "get_categories")

        result = json.loads(await tool.handler())
        assert result["categories"] == []
        assert "not connected" in result["message"]

    async def test_returns_categories_from_repo(self):
        mock_repo = AsyncMock()
        categories = ["work", "personal", "ideas"]

        with (
            patch("src.tools.get_github_settings", return_value=mock_repo),
            patch("src.tools.get_existing_categories", return_value=categories),
        ):
            tools = get_tools(CHAT_ID)
            tool = next(t for t in tools if t.name == "get_categories")

            result = json.loads(await tool.handler())
            assert result["categories"] == ["work", "personal", "ideas"]
            assert result["count"] == 3

    async def test_handles_fetch_error(self):
        mock_repo = AsyncMock()

        with (
            patch("src.tools.get_github_settings", return_value=mock_repo),
            patch("src.tools.get_existing_categories", side_effect=Exception("API error")),
        ):
            tools = get_tools(CHAT_ID)
            tool = next(t for t in tools if t.name == "get_categories")

            result = json.loads(await tool.handler())
            assert result["categories"] == []
            assert "Failed" in result["message"]
