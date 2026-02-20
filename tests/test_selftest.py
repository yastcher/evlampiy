"""Tests for startup self-test module."""

from unittest.mock import AsyncMock, patch

from src import const
from src.selftest import run_selftest

SAMPLE_AUDIO = b"fake_ogg_audio_data"
SAMPLE_DURATION = 5
ADMIN_ID = "12345"


async def test_sends_voice_and_transcription_to_admin(mock_bot, _patch_settings):
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = ("привет мир", 5, 1)
        await run_selftest(mock_bot)

    mock_bot.send_voice.assert_called_once_with(
        chat_id=int(ADMIN_ID), voice=SAMPLE_AUDIO, duration=SAMPLE_DURATION
    )
    mock_bot.send_message.assert_called_once()
    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u2705 Wit.ai \u2014 OK" in message_text
    assert "\u00abпривет мир\u00bb" in message_text  # noqa: RUF001


async def test_sends_error_on_empty_transcription(mock_bot, _patch_settings):
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = ("", 5, 0)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u274c Wit.ai \u2014 transcription returned empty text" in message_text


async def test_sends_error_on_transcription_exception(mock_bot, _patch_settings):
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.side_effect = RuntimeError("connection timeout")
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u274c Wit.ai \u2014 error: connection timeout" in message_text


async def test_uses_russian_language(mock_bot, _patch_settings):
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = ("текст", 3, 1)
        await run_selftest(mock_bot)

    mock_transcribe.assert_called_once_with(SAMPLE_AUDIO, "ogg", "ru", provider=const.PROVIDER_WIT)
    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "Self-test (ru)" in message_text


async def test_does_not_crash_on_send_failure(mock_bot, _patch_settings, caplog):
    mock_bot.send_message.side_effect = RuntimeError("chat not found")
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    assert "Self-test failed for admin" in caplog.text


async def test_skips_when_no_admins(mock_bot):
    with patch("src.selftest.settings") as mock_settings:
        mock_settings.admin_user_ids = set()
        await run_selftest(mock_bot)

    mock_bot.send_voice.assert_not_called()
    mock_bot.send_message.assert_not_called()


async def test_skips_when_sample_file_missing(mock_bot, caplog):
    with patch("src.selftest.settings") as mock_settings:
        mock_settings.admin_user_ids = {ADMIN_ID}
        mock_settings.selftest_sample_path = "/nonexistent/path/audio.ogg"
        await run_selftest(mock_bot)

    mock_bot.send_voice.assert_not_called()
    assert "Self-test sample file not found" in caplog.text


async def test_message_contains_version(mock_bot, _patch_settings):
    with (
        patch("src.selftest._get_version", return_value="0.7.0"),
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
    ):
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "v0.7.0" in message_text


async def test_groq_skipped_when_not_configured(mock_bot, _patch_settings):
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = ("текст", 3, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u274c Groq \u2014 skipped (not configured)" in message_text
    mock_transcribe.assert_called_once()


async def test_groq_success(mock_bot, _patch_settings):
    _patch_settings.groq_api_key = "test-key"
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = ("привет мир", 5, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u2705 Wit.ai \u2014 OK" in message_text
    assert "\u2705 Groq \u2014 OK" in message_text
    assert mock_transcribe.call_count == 2


async def test_groq_error_wit_ok(mock_bot, _patch_settings):
    _patch_settings.groq_api_key = "test-key"
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.side_effect = [("привет мир", 5, 1), RuntimeError("groq timeout")]
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u2705 Wit.ai \u2014 OK" in message_text
    assert "\u274c Groq \u2014 error: groq timeout" in message_text


async def test_sends_to_multiple_admins(mock_bot, _patch_settings):
    _patch_settings.admin_user_ids = {"12345", "67890"}
    with patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    assert mock_bot.send_voice.call_count == 2
    assert mock_bot.send_message.call_count == 2
    chat_ids = {call[1]["chat_id"] for call in mock_bot.send_voice.call_args_list}
    assert chat_ids == {12345, 67890}
