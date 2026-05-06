"""Tests for src.services.settings_service."""

from src.mongo import (
    get_auto_cleanup,
    get_preferred_provider,
    set_auto_cleanup,
    set_preferred_provider,
)
from src.services.settings_service import set_chat_provider_choice, toggle_auto_cleanup


class TestToggleAutoCleanup:
    async def test_off_to_on(self):
        chat_id = "u_settings_1"
        await set_auto_cleanup(chat_id, False)
        new_value = await toggle_auto_cleanup(chat_id)
        assert new_value is True
        assert await get_auto_cleanup(chat_id) is True

    async def test_on_to_off(self):
        chat_id = "u_settings_2"
        await set_auto_cleanup(chat_id, True)
        new_value = await toggle_auto_cleanup(chat_id)
        assert new_value is False
        assert await get_auto_cleanup(chat_id) is False


class TestSetChatProviderChoice:
    async def test_auto_clears_preference(self):
        chat_id = "u_settings_3"
        await set_preferred_provider(chat_id, "wit")
        key = await set_chat_provider_choice(chat_id, "auto")
        assert key == "choose_my_provider_auto"
        assert await get_preferred_provider(chat_id) is None

    async def test_wit_persists(self):
        chat_id = "u_settings_4"
        key = await set_chat_provider_choice(chat_id, "wit")
        assert key == "choose_my_provider_wit"
        assert await get_preferred_provider(chat_id) == "wit"

    async def test_groq_persists(self):
        chat_id = "u_settings_5"
        key = await set_chat_provider_choice(chat_id, "groq")
        assert key == "choose_my_provider_groq"
        assert await get_preferred_provider(chat_id) == "groq"

    async def test_unknown_choice_falls_back_to_auto(self):
        chat_id = "u_settings_6"
        await set_preferred_provider(chat_id, "wit")
        key = await set_chat_provider_choice(chat_id, "nonsense")
        assert key == "choose_my_provider_auto"
        assert await get_preferred_provider(chat_id) is None
