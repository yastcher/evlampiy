"""Per-chat settings use-case service. Framework-agnostic — no aiogram/pywa."""

from src import const
from src.mongo import get_auto_cleanup, set_auto_cleanup, set_preferred_provider
from src.types import ChatId

# Map UI choice → (persisted provider value, confirmation translation key).
# `None` means "auto-select per tier and availability" (the default).
_PROVIDER_CHOICES: dict[str, tuple[str | None, str]] = {
    "auto": (None, "choose_my_provider_auto"),
    "wit": (const.PROVIDER_WIT, "choose_my_provider_wit"),
    "groq": (const.PROVIDER_GROQ, "choose_my_provider_groq"),
}


async def toggle_auto_cleanup(chat_id: ChatId) -> bool:
    """Flip the auto-cleanup flag and return the new value."""
    new_value = not await get_auto_cleanup(chat_id)
    await set_auto_cleanup(chat_id, new_value)
    return new_value


async def set_chat_provider_choice(chat_id: ChatId, choice: str) -> str:
    """Persist the user-chosen transcription provider for a chat.

    ``choice`` is the UI token (``auto``/``wit``/``groq``). Unknown choices fall back to
    auto. Returns the localization key the caller should display to confirm the change.
    """
    provider_value, translate_key = _PROVIDER_CHOICES.get(choice, (None, "choose_my_provider_auto"))
    await set_preferred_provider(chat_id, provider_value)
    return translate_key
