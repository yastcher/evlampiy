"""Startup self-test: verify transcription pipeline and notify admins."""

import asyncio
import importlib.metadata
import logging
import pathlib
import tomllib

from aiogram import Bot
from aiogram.types import BufferedInputFile

from src import const
from src.ai_client import cleanup_text
from src.config import LANGUAGES, RUSSIAN, settings
from src.localization import translates
from src.prompts import CLEANUP_PROMPT_BASE
from src.transcription.service import get_audio_duration_seconds, transcribe_audio

logger = logging.getLogger(__name__)

_ResultList = list[tuple[str, str, str | None]]
_Section = tuple[str, _ResultList]

_PYPROJECT_PATH = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"


def _get_version() -> str:
    try:
        return importlib.metadata.version("evlampiy")
    except importlib.metadata.PackageNotFoundError:
        pass
    candidates = [
        _PYPROJECT_PATH,
        pathlib.Path("pyproject.toml"),
    ]
    for path in candidates:
        try:
            with path.open("rb") as f:
                return str(tomllib.load(f)["project"]["version"])
        except Exception:
            logger.debug("Could not read version from %s", path)
    return "unknown"


_WIT_LABEL = "Wit.ai"
_GROQ_LABEL = "Groq"
_CLEANUP_LABEL = "LLM cleanup"
_L10N_LABEL = "Localization"
_CONFIG_LABEL = "Config"

_CLEANUP_SAMPLE = "ну эм значит вот я сегодня аа ходил в магазин и купил молоко"  # noqa: RUF001

_PROVIDER_KEY_MAP: dict[str, str] = {
    const.PROVIDER_DEEPSEEK: "deepseek_api_key",
    const.PROVIDER_GEMINI: "gemini_api_key",
    const.PROVIDER_GROQ: "groq_api_key",
    const.PROVIDER_OPENROUTER: "openrouter_api_key",
    const.PROVIDER_QWEN: "qwen_api_key",
    const.PROVIDER_ANTHROPIC: "anthropic_bot_api_key",
    const.PROVIDER_OPENAI: "gpt_token",
}


def _format_result(label: str, text: str, error: str | None) -> str:
    """Format result line(s) for a single check."""
    if error:
        return f"\u274c {label} \u2014 {error}"
    if not text:
        return f"\u274c {label} \u2014 returned empty"
    return f"\u2705 {label} \u2014 {text}"


def _build_message(version: str, sections: list[_Section]) -> str:
    header = f"\U0001f680 Evlampiy v{version} deployed"
    lines = [header]
    for title, results in sections:
        lines.append("")
        lines.append(title)
        for label, text, error in results:
            lines.append(_format_result(label, text, error))
    return "\n".join(lines)


async def _test_provider(
    audio_bytes: bytes, audio_format: str, language: str, *, provider: str
) -> tuple[str, str | None]:
    """Run transcription for a single provider, return (text, error_message)."""
    try:
        text, _, _ = await transcribe_audio(audio_bytes, audio_format, language, provider=provider)
        return text, None
    except Exception as exc:
        return "", f"error: {exc}"


async def _test_cleanup() -> tuple[str, str | None]:
    """Test LLM cleanup pipeline, return (cleaned_text, error_or_none)."""
    prompt = f"{CLEANUP_PROMPT_BASE}\nTranscription:\n{_CLEANUP_SAMPLE}"
    try:
        result = await asyncio.wait_for(cleanup_text(prompt, max_tokens=200), timeout=60.0)
        if not result or not result.strip():
            return "", "LLM returned empty response"
        return f"\u00ab{result.strip()}\u00bb", None
    except TimeoutError:
        return "", "timeout (>60s)"
    except Exception as exc:
        return "", f"error: {exc}"


def _test_localization() -> tuple[str, str | None]:
    """Check all translation keys have all 4 languages."""
    missing: list[str] = []
    for key, langs in translates.items():
        for lang in LANGUAGES:
            if lang not in langs:
                missing.append(f"{key}:{lang}")
    if missing:
        return "", f"missing: {', '.join(missing[:5])}"
    return f"{len(translates)} keys OK", None


def _test_config() -> tuple[str, str | None]:
    """Check that selected providers have API keys configured."""
    warnings: list[str] = []
    for role, provider in [
        ("gpt_provider", settings.gpt_provider),
        ("categorization_provider", settings.categorization_provider),
    ]:
        key_attr = _PROVIDER_KEY_MAP.get(provider)
        if key_attr and not getattr(settings, key_attr, ""):
            warnings.append(f"{role}={provider} (no key)")
    wit_attr = f"wit_{settings.default_language}_token"
    if not getattr(settings, wit_attr, ""):
        warnings.append(f"wit ({settings.default_language}) (no token)")
    if warnings:
        return "", f"misconfigured: {', '.join(warnings)}"
    return "OK", None


async def run_selftest(bot: Bot) -> None:
    """Run transcription self-test and send results to admins."""
    try:
        await _run_selftest_inner(bot)
    except Exception:
        logger.exception("Self-test failed unexpectedly")


async def _run_selftest_inner(bot: Bot) -> None:
    admin_ids = settings.admin_user_ids
    if not admin_ids:
        logger.debug("No admin_user_ids configured, skipping self-test")
        return

    sample_path = pathlib.Path(settings.selftest_sample_path)
    if not sample_path.exists():
        logger.warning("Self-test sample file not found: %s", sample_path)
        return

    audio_bytes = sample_path.read_bytes()
    duration = get_audio_duration_seconds(audio_bytes, "ogg")
    version = _get_version()

    for admin_id in admin_ids:
        try:
            await _selftest_for_admin(bot, admin_id, audio_bytes, duration, version)
        except Exception:
            logger.exception("Self-test failed for admin %s", admin_id)


async def _selftest_for_admin(
    bot: Bot, admin_id: str, audio_bytes: bytes, duration: int, version: str
) -> None:
    language = RUSSIAN
    # todo =Y change it later
    # language = await get_chat_language(f"u_{admin_id}")

    # --- Transcription providers ---
    transcription_results: _ResultList = []

    wit_text, wit_error = await _test_provider(
        audio_bytes, "ogg", language, provider=const.PROVIDER_WIT
    )
    transcription_results.append((_WIT_LABEL, wit_text, wit_error))

    if settings.groq_api_key:
        groq_text, groq_error = await _test_provider(
            audio_bytes, "ogg", language, provider=const.PROVIDER_GROQ
        )
        transcription_results.append((_GROQ_LABEL, groq_text, groq_error))
    else:
        transcription_results.append((_GROQ_LABEL, "", "skipped (not configured)"))

    # --- LLM cleanup ---
    cleanup_results: _ResultList = []
    cleanup_text_result, cleanup_error = await _test_cleanup()
    cleanup_results.append((_CLEANUP_LABEL, cleanup_text_result, cleanup_error))

    # --- System checks ---
    system_results: _ResultList = []
    l10n_text, l10n_error = _test_localization()
    system_results.append((_L10N_LABEL, l10n_text, l10n_error))

    config_text, config_error = _test_config()
    system_results.append((_CONFIG_LABEL, config_text, config_error))

    sections: list[_Section] = [
        (f"\U0001f3a4 Self-test ({language}):", transcription_results),
        ("\U0001f9f9 LLM cleanup:", cleanup_results),
        ("\U0001f527 System checks:", system_results),
    ]

    message = _build_message(version, sections)
    chat_id = int(admin_id)
    voice_file = BufferedInputFile(audio_bytes, filename="selftest.ogg")
    await bot.send_voice(chat_id=chat_id, voice=voice_file, duration=duration)
    await bot.send_message(chat_id=chat_id, text=message)
