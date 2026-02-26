"""Tests for startup self-test module."""

from unittest.mock import AsyncMock, patch

from src import const
from src.selftest import _test_config, _test_localization, run_selftest

SAMPLE_AUDIO = b"fake_ogg_audio_data"
SAMPLE_DURATION = 5
ADMIN_ID = "12345"


def _mock_cleanup(return_value="cleaned text"):
    return patch("src.selftest.cleanup_text", new_callable=AsyncMock, return_value=return_value)


# --- Transcription provider tests ---


async def test_sends_voice_and_transcription_to_admin(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
        mock_transcribe.return_value = ("привет мир", 5, 1)
        await run_selftest(mock_bot)

    mock_bot.send_voice.assert_called_once_with(
        chat_id=int(ADMIN_ID), voice=SAMPLE_AUDIO, duration=SAMPLE_DURATION
    )
    mock_bot.send_message.assert_called_once()
    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u2705 Wit.ai" in message_text
    assert "привет мир" in message_text


async def test_sends_error_on_empty_transcription(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
        mock_transcribe.return_value = ("", 5, 0)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u274c Wit.ai \u2014 returned empty" in message_text


async def test_sends_error_on_transcription_exception(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
        mock_transcribe.side_effect = RuntimeError("connection timeout")
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u274c Wit.ai \u2014 error: connection timeout" in message_text


async def test_uses_russian_language(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
        mock_transcribe.return_value = ("текст", 3, 1)
        await run_selftest(mock_bot)

    mock_transcribe.assert_called_once_with(SAMPLE_AUDIO, "ogg", "ru", provider=const.PROVIDER_WIT)
    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "Self-test (ru)" in message_text


async def test_does_not_crash_on_send_failure(mock_bot, _patch_settings, caplog):
    mock_bot.send_message.side_effect = RuntimeError("chat not found")
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
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
        _mock_cleanup(),
    ):
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "v0.7.0" in message_text


async def test_groq_skipped_when_not_configured(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
        mock_transcribe.return_value = ("текст", 3, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u274c Groq \u2014 skipped (not configured)" in message_text
    mock_transcribe.assert_called_once()


async def test_groq_success(mock_bot, _patch_settings):
    _patch_settings.groq_api_key = "test-key"
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
        mock_transcribe.return_value = ("привет мир", 5, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u2705 Wit.ai" in message_text
    assert "\u2705 Groq" in message_text
    assert mock_transcribe.call_count == 2


async def test_groq_error_wit_ok(mock_bot, _patch_settings):
    _patch_settings.groq_api_key = "test-key"
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
        mock_transcribe.side_effect = [("привет мир", 5, 1), RuntimeError("groq timeout")]
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u2705 Wit.ai" in message_text
    assert "\u274c Groq \u2014 error: groq timeout" in message_text


async def test_sends_to_multiple_admins(mock_bot, _patch_settings):
    _patch_settings.admin_user_ids = {"12345", "67890"}
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(),
    ):
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    assert mock_bot.send_voice.call_count == 2
    assert mock_bot.send_message.call_count == 2
    chat_ids = {call[1]["chat_id"] for call in mock_bot.send_voice.call_args_list}
    assert chat_ids == {12345, 67890}


# --- LLM cleanup tests ---


async def test_cleanup_success(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup("я сегодня ходил в магазин и купил молоко"),
    ):
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u2705 LLM cleanup" in message_text
    assert "я сегодня ходил в магазин" in message_text


async def test_cleanup_error(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        patch(
            "src.selftest.cleanup_text",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API error"),
        ),
    ):
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u274c LLM cleanup \u2014 error: API error" in message_text


async def test_cleanup_empty_response(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup(None),
    ):
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "\u274c LLM cleanup \u2014 LLM returned empty response" in message_text


# --- Localization tests ---


def test_localization_all_present():
    text, error = _test_localization()
    assert error is None
    assert "keys OK" in text


def test_localization_missing_key():
    fake_translates = {
        "test_key": {"en": "Test", "ru": "Тест"},  # missing es, de
    }
    with patch("src.selftest.translates", fake_translates):
        text, error = _test_localization()
    assert text == ""
    assert error is not None
    assert "missing:" in error
    assert "test_key:es" in error


# --- Config coherence tests ---


def test_config_all_ok():
    with patch("src.selftest.settings") as mock_settings:
        mock_settings.gpt_provider = "deepseek"
        mock_settings.categorization_provider = "deepseek"
        mock_settings.deepseek_api_key = "key-123"
        mock_settings.default_language = "ru"
        mock_settings.wit_ru_token = "wit-token"
        text, error = _test_config()
    assert error is None
    assert text == "OK"


def test_config_missing_provider_key():
    with patch("src.selftest.settings") as mock_settings:
        mock_settings.gpt_provider = "deepseek"
        mock_settings.categorization_provider = "deepseek"
        mock_settings.deepseek_api_key = ""
        mock_settings.default_language = "ru"
        mock_settings.wit_ru_token = "wit-token"
        text, error = _test_config()
    assert text == ""
    assert error is not None
    assert "gpt_provider=deepseek (no key)" in error


def test_config_missing_wit_token():
    with patch("src.selftest.settings") as mock_settings:
        mock_settings.gpt_provider = "deepseek"
        mock_settings.categorization_provider = "deepseek"
        mock_settings.deepseek_api_key = "key-123"
        mock_settings.default_language = "ru"
        mock_settings.wit_ru_token = ""
        text, error = _test_config()
    assert text == ""
    assert error is not None
    assert "wit (ru) (no token)" in error


def test_config_multiple_warnings():
    with patch("src.selftest.settings") as mock_settings:
        mock_settings.gpt_provider = "gemini"
        mock_settings.categorization_provider = "deepseek"
        mock_settings.gemini_api_key = ""
        mock_settings.deepseek_api_key = ""
        mock_settings.default_language = "en"
        mock_settings.wit_en_token = ""
        text, error = _test_config()
    assert text == ""
    assert error is not None
    assert "gpt_provider=gemini (no key)" in error
    assert "categorization_provider=deepseek (no key)" in error
    assert "wit (en) (no token)" in error


# --- Message sections ---


async def test_message_has_all_sections(mock_bot, _patch_settings):
    with (
        patch("src.selftest.transcribe_audio", new_callable=AsyncMock) as mock_transcribe,
        _mock_cleanup("cleaned"),
    ):
        mock_transcribe.return_value = ("text", 2, 1)
        await run_selftest(mock_bot)

    message_text = mock_bot.send_message.call_args[1]["text"]
    assert "Self-test (ru):" in message_text
    assert "LLM cleanup:" in message_text
    assert "System checks:" in message_text
    assert "\u2705 Localization" in message_text
    assert "\u2705 Config" in message_text
