"""Tests for account linking between Telegram and WhatsApp."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.account_linking import (
    LINK_CODE_LENGTH,
    LINK_CODE_TTL_SECONDS,
    confirm_link,
    generate_link_code,
    get_linked_telegram_id,
    get_linked_whatsapp,
    unlink,
)
from src.dto import LinkCode

pytestmark = [pytest.mark.asyncio]


class TestAccountLinking:
    """Full account linking lifecycle."""

    async def test_complete_linking_flow(self):
        """Generate code → confirm → check link → unlink."""
        telegram_user_id = "111222"
        whatsapp_phone = "79001234567"

        # 1. Generate code
        code = await generate_link_code(telegram_user_id)
        assert len(code) == LINK_CODE_LENGTH
        assert code.isdigit()

        # 2. No link yet
        assert await get_linked_telegram_id(whatsapp_phone) is None
        assert await get_linked_whatsapp(telegram_user_id) is None

        # 3. Confirm link
        result = await confirm_link(code, whatsapp_phone)
        assert result is True

        # 4. Link exists both ways
        assert await get_linked_telegram_id(whatsapp_phone) == telegram_user_id
        assert await get_linked_whatsapp(telegram_user_id) == whatsapp_phone

        # 5. Unlink
        result = await unlink(telegram_user_id)
        assert result is True

        # 6. Link gone
        assert await get_linked_telegram_id(whatsapp_phone) is None
        assert await get_linked_whatsapp(telegram_user_id) is None

    async def test_invalid_code_rejected(self):
        """Invalid code returns False."""
        result = await confirm_link("000000", "79001234567")
        assert result is False

    async def test_expired_code_rejected(self):
        """Expired code returns False."""
        telegram_user_id = "333444"
        code = await generate_link_code(telegram_user_id)

        # Manually expire the code in DB
        record = await LinkCode.find_one(LinkCode.code == code)
        record.created_at = datetime.now(timezone.utc) - timedelta(seconds=LINK_CODE_TTL_SECONDS + 1)
        await record.save()

        result = await confirm_link(code, "79009999999")
        assert result is False

    async def test_new_code_invalidates_old(self):
        """Generating new code invalidates previous one."""
        telegram_user_id = "555666"

        old_code = await generate_link_code(telegram_user_id)
        new_code = await generate_link_code(telegram_user_id)

        # Old code should not work
        result = await confirm_link(old_code, "79001111111")
        assert result is False

        # New code works
        result = await confirm_link(new_code, "79001111111")
        assert result is True

    async def test_relinking_replaces_old_link(self):
        """New link replaces existing one for the same Telegram user."""
        user_a = "aaa111"
        phone_1 = "79001111111"
        phone_2 = "79002222222"

        # Link user_a ↔ phone_1
        code = await generate_link_code(user_a)
        await confirm_link(code, phone_1)
        assert await get_linked_whatsapp(user_a) == phone_1

        # Link user_a ↔ phone_2 (replaces)
        code = await generate_link_code(user_a)
        await confirm_link(code, phone_2)

        assert await get_linked_whatsapp(user_a) == phone_2
        assert await get_linked_telegram_id(phone_1) is None
        assert await get_linked_telegram_id(phone_2) == user_a

    async def test_whatsapp_phone_relinked_to_different_user(self):
        """If phone was linked to user_a, linking to user_b removes old link."""
        user_a = "userA"
        user_b = "userB"
        phone = "79003333333"

        code = await generate_link_code(user_a)
        await confirm_link(code, phone)
        assert await get_linked_telegram_id(phone) == user_a

        code = await generate_link_code(user_b)
        await confirm_link(code, phone)
        assert await get_linked_telegram_id(phone) == user_b
        assert await get_linked_whatsapp(user_a) is None

    async def test_unlink_nonexistent_returns_false(self):
        """Unlinking when no link exists returns False."""
        result = await unlink("nonexistent_user")
        assert result is False


class TestLinkWhatsAppCommand:
    """Test /link_whatsapp Telegram handler."""

    async def test_generates_code_in_private_chat(self, mock_private_update, mock_context):
        from src.telegram.handlers import link_whatsapp

        mock_private_update.effective_user.id = 12345

        await link_whatsapp(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "link" in reply_text.lower()
        assert "WhatsApp" in reply_text

    async def test_ignored_in_group_chat(self, mock_group_update, mock_context):
        from src.telegram.handlers import link_whatsapp

        await link_whatsapp(mock_group_update, mock_context)

        mock_group_update.message.reply_text.assert_not_called()


class TestUnlinkWhatsAppCommand:
    """Test /unlink_whatsapp Telegram handler."""

    async def test_unlinks_existing(self, mock_private_update, mock_context):
        from src.telegram.handlers import unlink_whatsapp

        user_id = "12345"
        mock_private_update.effective_user.id = 12345

        # Create a link first
        code = await generate_link_code(user_id)
        await confirm_link(code, "79001234567")

        await unlink_whatsapp(mock_private_update, mock_context)

        mock_private_update.message.reply_text.assert_called_once()
        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "unlinked" in reply_text.lower()

    async def test_handles_no_link(self, mock_private_update, mock_context):
        from src.telegram.handlers import unlink_whatsapp

        mock_private_update.effective_user.id = 99999

        await unlink_whatsapp(mock_private_update, mock_context)

        reply_text = mock_private_update.message.reply_text.call_args[0][0]
        assert "no" in reply_text.lower()


class TestWhatsAppLinkHandler:
    """Test WhatsApp link command handling."""

    async def test_links_with_valid_code(self):
        from src.whatsapp.handlers import handle_link_command

        user_id = "tg_user_42"
        phone = "79001234567"
        code = await generate_link_code(user_id)

        mock_wa = MagicMock()
        mock_wa.send_message = MagicMock()

        mock_message = MagicMock()
        mock_message.from_user.wa_id = phone
        mock_message.text = f"link {code}"

        await handle_link_command(mock_wa, mock_message)

        mock_wa.send_message.assert_called_once()
        call_kwargs = mock_wa.send_message.call_args
        assert "success" in call_kwargs.kwargs["text"].lower() or "success" in str(call_kwargs).lower()

        assert await get_linked_telegram_id(phone) == user_id

    async def test_rejects_invalid_code(self):
        from src.whatsapp.handlers import handle_link_command

        mock_wa = MagicMock()
        mock_wa.send_message = MagicMock()

        mock_message = MagicMock()
        mock_message.from_user.wa_id = "79001234567"
        mock_message.text = "link 000000"

        await handle_link_command(mock_wa, mock_message)

        call_text = mock_wa.send_message.call_args.kwargs["text"]
        assert "invalid" in call_text.lower() or "expired" in call_text.lower()
