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
    try:
        with _PYPROJECT_PATH.open("rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return "unknown"


def _build_message(version: str, language: str, text: str, error: str | None) -> str:
    header = f"\U0001f680 Evlampiy v{version} deployed"
    if error:
        return f"{header}\n\n\U0001f3a4 Self-test ({language}):\n\u274c Wit.ai \u2014 {error}"
    if not text:
        return (
            f"{header}\n\n\U0001f3a4 Self-test ({language}):\n"
            "\u274c Wit.ai \u2014 transcription returned empty text"
        )
    return (
        f"{header}\n\n\U0001f3a4 Self-test ({language}):\n"
        f"\U0001f4dd \u00ab{text}\u00bb\n\u2705 Wit.ai \u2014 OK"
    )


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

    text = ""
    error = None
    try:
        text, _ = await transcribe_audio(audio_bytes, "ogg", language, use_groq=False)
    except Exception as exc:
        error = f"error: {exc}"

    message = _build_message(version, language, text, error)
    chat_id = int(admin_id)
    await bot.send_voice(chat_id=chat_id, voice=audio_bytes, duration=duration)
    await bot.send_message(chat_id=chat_id, text=message)
