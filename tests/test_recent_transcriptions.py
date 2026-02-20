"""TROPHY-style pipeline tests for recent transcription context storage."""

from src.mongo import get_recent_transcriptions, save_recent_transcription


class TestRecentTranscriptionPipeline:
    """Pipeline integration tests: real DB (mongomock), no external mocks."""

    async def test_save_and_retrieve(self):
        """Saved transcription is returned for the same chat."""
        await save_recent_transcription("chat_1", "First note")
        result = await get_recent_transcriptions("chat_1")
        assert result == ["First note"]

    async def test_multiple_notes_returned(self):
        """Multiple saved notes are all returned."""
        await save_recent_transcription("chat_2", "Note A")
        await save_recent_transcription("chat_2", "Note B")
        await save_recent_transcription("chat_2", "Note C")

        result = await get_recent_transcriptions("chat_2")
        assert len(result) == 3
        assert set(result) == {"Note A", "Note B", "Note C"}

    async def test_limit_parameter_respected(self):
        """Only the requested number of recent notes is returned."""
        for i in range(5):
            await save_recent_transcription("chat_3", f"Note {i}")

        result = await get_recent_transcriptions("chat_3", limit=2)
        assert len(result) == 2

    async def test_isolated_per_chat(self):
        """Transcriptions from different chats do not mix."""
        await save_recent_transcription("chat_a", "Chat A note")
        await save_recent_transcription("chat_b", "Chat B note")

        result_a = await get_recent_transcriptions("chat_a")
        result_b = await get_recent_transcriptions("chat_b")

        assert result_a == ["Chat A note"]
        assert result_b == ["Chat B note"]

    async def test_empty_chat_returns_empty_list(self):
        """Returns [] when no transcriptions exist for a chat."""
        result = await get_recent_transcriptions("nonexistent_chat")
        assert result == []

    async def test_keeps_last_5_entries(self):
        """Only 5 transcriptions are kept per chat (oldest trimmed)."""
        for i in range(7):
            await save_recent_transcription("chat_trim", f"Note {i}")

        result = await get_recent_transcriptions("chat_trim", limit=10)
        assert len(result) == 5
