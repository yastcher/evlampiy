"""Service-level smoke tests for `src.services.voice_pipeline.process_voice`.

These tests call the service directly with `audio_bytes` — no aiogram or pywa mocks.
Telegram-adapter and WhatsApp-adapter behavior (validation, credits, gpt-command
formatting, send_message wiring) is covered by `tests/test_user_flow.py` and
`tests/test_whatsapp.py`.
"""

from unittest.mock import AsyncMock, patch

from src import const
from src.dto import UserTier
from src.mongo import set_auto_categorize, set_auto_cleanup, set_chat_language, set_github_settings
from src.services.voice_pipeline import VoicePipelineResult, process_voice


class TestProcessVoiceTranscription:
    """Trophy: real DB (mongomock); mock only external boundaries."""

    async def test_empty_transcription_returns_none(self):
        """Empty transcription → service returns None (caller skips reply)."""
        chat_id = "u_70001"
        await set_chat_language(chat_id, "en")
        with (
            patch(
                "src.services.voice_pipeline.transcribe_audio",
                AsyncMock(return_value=("", 0, 0)),
            ),
            patch(
                "src.services.voice_pipeline.save_transcription_to_obsidian",
                AsyncMock(return_value=(False, None)),
            ),
        ):
            result = await process_voice(
                audio_bytes=b"audio",
                audio_format="ogg",
                source=const.SOURCE_TELEGRAM,
                chat_id=chat_id,
                language="en",
                provider=const.PROVIDER_WIT,
                tier=UserTier.FREE,
            )
        assert result is None

    async def test_free_tier_skips_cleanup(self):
        """FREE tier: cleanup never runs, raw text returned."""
        chat_id = "u_70002"
        await set_chat_language(chat_id, "en")
        await set_auto_cleanup(chat_id, True)  # enabled but ignored for FREE
        with (
            patch(
                "src.services.voice_pipeline.transcribe_audio",
                AsyncMock(return_value=("raw text", 5, 1)),
            ),
            patch("src.services.voice_pipeline.cleanup_transcript", AsyncMock()) as mock_cleanup,
            patch(
                "src.services.voice_pipeline.save_transcription_to_obsidian",
                AsyncMock(return_value=(False, None)),
            ),
        ):
            result = await process_voice(
                audio_bytes=b"audio",
                audio_format="ogg",
                source=const.SOURCE_TELEGRAM,
                chat_id=chat_id,
                language="en",
                provider=const.PROVIDER_WIT,
                tier=UserTier.FREE,
            )
        assert result == VoicePipelineResult(text="raw text", duration=5, wit_requests=1)
        mock_cleanup.assert_not_called()

    async def test_paid_with_cleanup_on_returns_cleaned(self):
        """PAID tier + auto_cleanup=True: cleaned text is the reply text."""
        chat_id = "u_70003"
        await set_chat_language(chat_id, "en")
        await set_auto_cleanup(chat_id, True)
        with (
            patch(
                "src.services.voice_pipeline.transcribe_audio",
                AsyncMock(return_value=("ну вот текст", 5, 1)),
            ),
            patch(
                "src.services.voice_pipeline.cleanup_transcript",
                AsyncMock(return_value="Текст."),
            ) as mock_cleanup,
            patch(
                "src.services.voice_pipeline.save_transcription_to_obsidian",
                AsyncMock(return_value=(False, None)),
            ),
        ):
            result = await process_voice(
                audio_bytes=b"audio",
                audio_format="ogg",
                source=const.SOURCE_TELEGRAM,
                chat_id=chat_id,
                language="ru",
                provider=const.PROVIDER_GROQ,
                tier=UserTier.PAID,
            )
        assert result is not None
        assert result.text == "Текст."
        mock_cleanup.assert_called_once()

    async def test_paid_with_cleanup_off_keeps_raw_reply_but_cleans_obsidian(self):
        """PAID tier + auto_cleanup=False: raw text replied; cleaned text saved to Obsidian."""
        chat_id = "u_70004"
        await set_chat_language(chat_id, "en")
        await set_auto_cleanup(chat_id, False)
        raw, cleaned = "ну сырой текст", "Сырой текст."
        with (
            patch(
                "src.services.voice_pipeline.transcribe_audio",
                AsyncMock(return_value=(raw, 5, 1)),
            ),
            patch(
                "src.services.voice_pipeline.cleanup_transcript",
                AsyncMock(return_value=cleaned),
            ),
            patch(
                "src.services.voice_pipeline.save_transcription_to_obsidian",
                AsyncMock(return_value=(False, None)),
            ) as mock_save,
        ):
            result = await process_voice(
                audio_bytes=b"audio",
                audio_format="ogg",
                source=const.SOURCE_TELEGRAM,
                chat_id=chat_id,
                language="ru",
                provider=const.PROVIDER_GROQ,
                tier=UserTier.PAID,
            )
        assert result is not None
        assert result.text == raw  # reply gets RAW
        # Obsidian got CLEANED + original_text=raw
        save_kwargs = mock_save.call_args.kwargs
        save_args = mock_save.call_args.args
        assert save_args[1] == cleaned
        assert save_kwargs["original_text"] == raw

    async def test_auto_categorize_runs_when_obsidian_saved(self):
        """auto_categorize=True + obsidian saved + github settings → categorize_note called."""
        chat_id = "u_70005"
        await set_chat_language(chat_id, "en")
        await set_auto_categorize(chat_id, True)
        await set_github_settings(chat_id, "owner", "repo", "tok")
        with (
            patch(
                "src.services.voice_pipeline.transcribe_audio",
                AsyncMock(return_value=("note text", 5, 1)),
            ),
            patch(
                "src.services.voice_pipeline.save_transcription_to_obsidian",
                AsyncMock(return_value=(True, "note.md")),
            ),
            patch("src.services.voice_pipeline.categorize_note", AsyncMock()) as mock_categorize,
        ):
            await process_voice(
                audio_bytes=b"audio",
                audio_format="ogg",
                source=const.SOURCE_TELEGRAM,
                chat_id=chat_id,
                language="en",
                provider=const.PROVIDER_WIT,
                tier=UserTier.FREE,
            )
        mock_categorize.assert_called_once()

    async def test_settings_chat_id_lookup_for_group_chat(self):
        """When chat_id is `g_*`, settings_chat_id (passed by adapter) drives lookups."""
        group_chat = "g_500"
        user_settings = "u_555"
        await set_chat_language(user_settings, "en")
        await set_auto_cleanup(user_settings, True)
        with (
            patch(
                "src.services.voice_pipeline.transcribe_audio",
                AsyncMock(return_value=("text", 5, 1)),
            ),
            patch(
                "src.services.voice_pipeline.cleanup_transcript",
                AsyncMock(return_value="cleaned"),
            ) as mock_cleanup,
            patch(
                "src.services.voice_pipeline.save_transcription_to_obsidian",
                AsyncMock(return_value=(False, None)),
            ),
        ):
            await process_voice(
                audio_bytes=b"audio",
                audio_format="ogg",
                source=const.SOURCE_TELEGRAM,
                chat_id=group_chat,
                language="en",
                provider=const.PROVIDER_WIT,
                tier=UserTier.PAID,
                settings_chat_id=user_settings,
            )
        # cleanup is called → settings_chat_id was honored (auto_cleanup lookup hit user_settings)
        mock_cleanup.assert_called_once()
