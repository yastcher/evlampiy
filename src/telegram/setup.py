"""Telegram application setup: handler registration and bot initialization."""

import logging

from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from src.config import settings
from src.gpt_commands import evlampiy_command
from src.selftest import run_selftest
from src.telegram import admin, handlers
from src.telegram.payments import (
    balance_command,
    buy_command,
    buy_package_callback,
    handle_pre_checkout,
    handle_successful_payment,
)
from src.telegram.voice import from_voice_to_text

logger = logging.getLogger(__name__)

COMMAND_HANDLERS = {
    "start": handlers.start,
    "settings": handlers.settings_hub,
    "obsidian": handlers.obsidian_hub,
    "account": handlers.account_hub,
    "choose_your_language": handlers.choose_language,
    "enter_your_command": handlers.enter_your_command,
    "evlampiy": evlampiy_command,
    "connect_github": handlers.connect_github,
    "toggle_obsidian": handlers.toggle_obsidian,
    "disconnect_github": handlers.disconnect_github,
    "buy": buy_command,
    "balance": balance_command,
    "mystats": handlers.mystats_command,
    "stats": handlers.stats_command,
    "admin": admin.admin_hub,
    "add_vip": admin.add_vip_command,
    "remove_vip": admin.remove_vip_command,
    "add_tester": admin.add_tester_command,
    "remove_tester": admin.remove_tester_command,
    "add_credits": admin.add_credits_command,
    "block": admin.block_command,
    "unblock": admin.unblock_command,
    "toggle_categorize": handlers.toggle_categorize,
    "categorize": handlers.categorize_all,
    "link_whatsapp": handlers.link_whatsapp,
    "unlink_whatsapp": handlers.unlink_whatsapp,
}

BOT_COMMANDS = {
    "en": [
        BotCommand("start", "Start work"),
        BotCommand("settings", "⚙️ Settings"),
        BotCommand("obsidian", "📝 Notes"),
        BotCommand("account", "💰 Account"),
    ],
    "ru": [
        BotCommand("start", "Начать работу"),
        BotCommand("settings", "⚙️ Настройки"),
        BotCommand("obsidian", "📝 Заметки"),
        BotCommand("account", "💰 Аккаунт"),
    ],
    "es": [
        BotCommand("start", "Iniciar"),
        BotCommand("settings", "⚙️ Configuración"),
        BotCommand("obsidian", "📝 Notas"),
        BotCommand("account", "💰 Cuenta"),
    ],
    "de": [
        BotCommand("start", "Starten"),
        BotCommand("settings", "⚙️ Einstellungen"),
        BotCommand("obsidian", "📝 Notizen"),
        BotCommand("account", "💰 Konto"),
    ],
}

ADMIN_COMMANDS = [
    BotCommand("admin", "🔧 Admin panel"),
    BotCommand("stats", "📊 System stats"),
    BotCommand("add_vip", "⭐ Add VIP user"),
    BotCommand("remove_vip", "⭐ Remove VIP user"),
    BotCommand("add_tester", "🧪 Add tester"),
    BotCommand("remove_tester", "🧪 Remove tester"),
    BotCommand("add_credits", "💰 Add credits to user"),
    BotCommand("block", "🚫 Block user"),
    BotCommand("unblock", "✅ Unblock user"),
]


async def post_init(application: Application):
    bot = application.bot

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

    await run_selftest(bot)


def build_application() -> Application:
    """Build and configure the Telegram Application with all handlers."""
    application = (
        ApplicationBuilder().token(settings.telegram_bot_token).post_init(post_init).build()
    )

    for command_name, command_handler in COMMAND_HANDLERS.items():
        application.add_handler(CommandHandler(command_name, command_handler))

    application.add_handler(CallbackQueryHandler(handlers.lang_buttons, pattern="^set_lang_"))
    application.add_handler(CallbackQueryHandler(handlers.provider_buttons, pattern="^set_prov_"))
    application.add_handler(CallbackQueryHandler(handlers.hub_callback_router, pattern="^hub_"))
    application.add_handler(CallbackQueryHandler(admin.admin_callback_router, pattern="^adm_"))
    application.add_handler(CallbackQueryHandler(buy_package_callback, pattern="^buy_pkg_"))

    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, from_voice_to_text))

    application.add_handler(PreCheckoutQueryHandler(handle_pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, handle_successful_payment))

    enter_command_handler = ConversationHandler(
        entry_points=[
            CommandHandler("enter_your_command", handlers.enter_your_command),
            CallbackQueryHandler(handlers.enter_your_command_from_hub, pattern="^hub_gpt_command$"),
        ],
        states={
            handlers.WAITING_FOR_COMMAND: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_command_input)
            ]
        },
        fallbacks=[],
    )
    application.add_handler(enter_command_handler)

    return application
