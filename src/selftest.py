"""Startup self-test: verify transcription pipeline and notify admins."""

import importlib.metadata
import logging
import pathlib
import tomllib

import telegram

from src.config import RUSSIAN, settings
from src.transcription.service import get_audio_duration_seconds, transcribe_audio

logger = logging.getLogger(__name__)


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
                return tomllib.load(f)["project"]["version"]
        except Exception:
            logger.debug("Could not read version from %s", path)
    return "unknown"


_WIT_LABEL = "Wit.ai"
_GROQ_LABEL = "Groq"


def _format_provider_result(provider: str, text: str, error: str | None) -> str:
    """Format result line(s) for a single transcription provider."""
    if error:
        return f"\u274c {provider} \u2014 {error}"
    if not text:
        return f"\u274c {provider} \u2014 transcription returned empty text"
    return f"\U0001f4dd \u00ab{text}\u00bb\n\u2705 {provider} \u2014 OK"


def _build_message(version: str, language: str, results: list[tuple[str, str, str | None]]) -> str:
    header = f"\U0001f680 Evlampiy v{version} deployed"
    lines = [header, "", f"\U0001f3a4 Self-test ({language}):"]
    for provider, text, error in results:
        lines.append(_format_provider_result(provider, text, error))
    return "\n".join(lines)


async def _test_provider(
    audio_bytes: bytes, audio_format: str, language: str, *, use_groq: bool
) -> tuple[str, str | None]:
    """Run transcription for a single provider, return (text, error_message)."""
    try:
        text, _ = await transcribe_audio(audio_bytes, audio_format, language, use_groq=use_groq)
        return text, None
    except Exception as exc:
        return "", f"error: {exc}"


async def run_selftest(bot: telegram.Bot) -> None:
    """Run transcription self-test and send results to admins."""
    try:
        await _run_selftest_inner(bot)
    except Exception:
        logger.exception("Self-test failed unexpectedly")


async def _run_selftest_inner(bot: telegram.Bot) -> None:
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
    bot: telegram.Bot, admin_id: str, audio_bytes: bytes, duration: int, version: str
) -> None:
    language = RUSSIAN
    # todo =Y change it later
    # language = await get_chat_language(f"u_{admin_id}")

    results: list[tuple[str, str, str | None]] = []

    # Test Wit.ai
    wit_text, wit_error = await _test_provider(audio_bytes, "ogg", language, use_groq=False)
    results.append((_WIT_LABEL, wit_text, wit_error))

    # Test Groq
    if settings.groq_api_key:
        groq_text, groq_error = await _test_provider(audio_bytes, "ogg", language, use_groq=True)
        results.append((_GROQ_LABEL, groq_text, groq_error))
    else:
        results.append((_GROQ_LABEL, "", "skipped (not configured)"))

    message = _build_message(version, language, results)
    chat_id = int(admin_id)
    await bot.send_voice(chat_id=chat_id, voice=audio_bytes, duration=duration)
    await bot.send_message(chat_id=chat_id, text=message)
