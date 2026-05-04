"""Telegram application setup: handler registration and bot initialization."""

import asyncio
import logging
import typing

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    Message,
    TelegramObject,
    Update,
)

from src.config import settings
from src.gpt_commands import evlampiy_command
from src.selftest import run_selftest
from src.telegram import account_handlers, admin, handlers, obsidian_handlers, settings_handlers
from src.telegram.handlers import GptCommandStates
from src.telegram.payments import (
    balance_command,
    buy_command,
    buy_package_callback,
    handle_pre_checkout,
    handle_successful_payment,
)
from src.telegram.voice import from_voice_to_text

logger = logging.getLogger(__name__)

COMMAND_HANDLERS: dict[str, typing.Callable[..., typing.Awaitable[typing.Any]]] = {
    "start": handlers.start,
    "settings": settings_handlers.settings_hub,
    "obsidian": obsidian_handlers.obsidian_hub,
    "account": account_handlers.account_hub,
    "choose_your_language": settings_handlers.choose_language,
    "enter_your_command": handlers.enter_your_command,
    "evlampiy": evlampiy_command,
    "connect_github": obsidian_handlers.connect_github,
    "toggle_obsidian": obsidian_handlers.toggle_obsidian,
    "disconnect_github": obsidian_handlers.disconnect_github,
    "buy": buy_command,
    "balance": balance_command,
    "mystats": account_handlers.mystats_command,
    "stats": handlers.stats_command,
    "admin": admin.admin_hub,
    "add_vip": admin.add_vip_command,
    "remove_vip": admin.remove_vip_command,
    "add_tester": admin.add_tester_command,
    "remove_tester": admin.remove_tester_command,
    "add_credits": admin.add_credits_command,
    "block": admin.block_command,
    "unblock": admin.unblock_command,
    "toggle_categorize": obsidian_handlers.toggle_categorize,
    "categorize": obsidian_handlers.categorize_all,
    "link_whatsapp": account_handlers.link_whatsapp,
    "unlink_whatsapp": account_handlers.unlink_whatsapp,
}

BOT_COMMANDS = {
    "en": [
        BotCommand(command="start", description="Start work"),
        BotCommand(command="settings", description="⚙️ Settings"),
        BotCommand(command="obsidian", description="📝 Notes"),
        BotCommand(command="account", description="💰 Account"),
    ],
    "ru": [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="obsidian", description="📝 Заметки"),
        BotCommand(command="account", description="💰 Аккаунт"),
    ],
    "es": [
        BotCommand(command="start", description="Iniciar"),
        BotCommand(command="settings", description="⚙️ Configuración"),
        BotCommand(command="obsidian", description="📝 Notas"),
        BotCommand(command="account", description="💰 Cuenta"),
    ],
    "de": [
        BotCommand(command="start", description="Starten"),
        BotCommand(command="settings", description="⚙️ Einstellungen"),
        BotCommand(command="obsidian", description="📝 Notizen"),
        BotCommand(command="account", description="💰 Konto"),
    ],
}

ADMIN_COMMANDS = [
    BotCommand(command="admin", description="🔧 Admin panel"),
    BotCommand(command="stats", description="📊 System stats"),
    BotCommand(command="add_vip", description="⭐ Add VIP user"),
    BotCommand(command="remove_vip", description="⭐ Remove VIP user"),
    BotCommand(command="add_tester", description="🧪 Add tester"),
    BotCommand(command="remove_tester", description="🧪 Remove tester"),
    BotCommand(command="add_credits", description="💰 Add credits to user"),
    BotCommand(command="block", description="🚫 Block user"),
    BotCommand(command="unblock", description="✅ Unblock user"),
]


class BotSenderRejectMiddleware(BaseMiddleware):
    """Outer middleware that drops updates originating from another Telegram bot.

    Equivalent to PTB's `TypeHandler(group=-1)` + `ApplicationHandlerStop` pattern.
    """

    async def __call__(
        self,
        handler: typing.Callable[
            [TelegramObject, dict[str, typing.Any]], typing.Awaitable[typing.Any]
        ],
        event: TelegramObject,
        data: dict[str, typing.Any],
    ) -> typing.Any:
        if isinstance(event, Update):
            inner = event.event
            user = getattr(inner, "from_user", None)
            if user is not None and getattr(user, "is_bot", False):
                logger.debug("Rejected update from bot sender: user_id=%s", user.id)
                return None
        return await handler(event, data)


async def setup_bot_commands(bot: Bot) -> None:
    """Register localized bot command menus and admin scopes."""
    for lang_code, commands in BOT_COMMANDS.items():
        await bot.set_my_commands(
            commands,
            scope=BotCommandScopeAllPrivateChats(),
            language_code=lang_code if lang_code != "en" else None,
        )

    for admin_id in settings.admin_user_ids:
        admin_commands = BOT_COMMANDS["en"] + ADMIN_COMMANDS
        await bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=int(admin_id)),
        )


def build_router() -> Router:
    """Build aiogram Router with all command and callback handlers."""
    router = Router()

    for command_name, command_handler in COMMAND_HANDLERS.items():
        router.message.register(command_handler, Command(command_name))

    router.callback_query.register(settings_handlers.lang_buttons, F.data.startswith("set_lang_"))
    router.callback_query.register(
        settings_handlers.provider_buttons, F.data.startswith("set_prov_")
    )
    # Conversation entry point for /enter_your_command via hub button
    router.callback_query.register(
        handlers.enter_your_command_from_hub, F.data == "hub_gpt_command"
    )
    router.callback_query.register(handlers.hub_callback_router, F.data.startswith("hub_"))
    router.callback_query.register(admin.admin_callback_router, F.data.startswith("adm_"))
    router.callback_query.register(buy_package_callback, F.data.startswith("buy_pkg_"))

    # Voice / audio messages
    router.message.register(from_voice_to_text, F.voice | F.audio)

    # Payments
    router.pre_checkout_query.register(handle_pre_checkout)
    router.message.register(handle_successful_payment, F.successful_payment)

    # Conversation: text input while in WAITING_FOR_COMMAND state
    router.message.register(
        handlers.handle_command_input,
        GptCommandStates.waiting,
        F.text,
        ~F.text.startswith("/"),
    )

    return router


def build_dispatcher() -> Dispatcher:
    """Build aiogram Dispatcher with middleware and routers."""
    dp = Dispatcher()
    dp.update.outer_middleware(BotSenderRejectMiddleware())
    dp.include_router(build_router())
    return dp


def build_bot() -> Bot:
    """Build aiogram Bot with default HTML parse mode for compatibility."""
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=None),
    )


async def run_bot() -> None:
    """Initialize bot, register commands, run self-test, and start polling."""
    bot = build_bot()
    dp = build_dispatcher()
    selftest_task: asyncio.Task[None] | None = None
    try:
        await setup_bot_commands(bot)
        # Selftest runs as a background task so a hanging provider never blocks polling.
        selftest_task = asyncio.create_task(run_selftest(bot), name="selftest")
        await dp.start_polling(bot)
    finally:
        if selftest_task is not None and not selftest_task.done():
            selftest_task.cancel()
        await bot.session.close()


__all__ = [
    "ADMIN_COMMANDS",
    "BOT_COMMANDS",
    "COMMAND_HANDLERS",
    "BotSenderRejectMiddleware",
    "Message",
    "build_bot",
    "build_dispatcher",
    "build_router",
    "run_bot",
    "setup_bot_commands",
]
