import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from src import const
from src.account_linking import generate_link_code, get_linked_whatsapp, unlink
from src.ai_client import _PROVIDER_LIMITS, CATEGORIZATION_FALLBACK_CHAIN, GPT_FALLBACK_CHAIN
from src.categorization import categorize_all_income
from src.config import settings
from src.credits import (
    current_month_key,
    get_monthly_stats,
    get_total_credits,
    get_user_tier,
    is_admin_user,
)
from src.dto import UserCredits, UserTier
from src.github_api import create_obsidian_git_config, get_or_create_obsidian_repo
from src.github_oauth import get_github_device_code, poll_github_for_token
from src.localization import translates
from src.mongo import (
    clear_github_settings,
    get_auto_categorize,
    get_auto_cleanup,
    get_bot_config,
    get_chat_language,
    get_github_settings,
    get_gpt_command,
    get_preferred_provider,
    get_save_to_obsidian,
    set_auto_categorize,
    set_auto_cleanup,
    set_chat_language,
    set_github_settings,
    set_gpt_command,
    set_preferred_provider,
    set_save_to_obsidian,
)
from src.telegram.chat_params import get_chat_id, is_private_chat, is_user_admin, reply_text
from src.telegram.payments import balance_command, buy_command
from src.wit_tracking import get_all_wit_usage_this_month

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()
WAITING_FOR_COMMAND = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    chat_language = await get_chat_language(chat_id)
    gpt_command = await get_gpt_command(chat_id)
    text_to_send = translates["start_message"][chat_language].format(
        chat_language=chat_language,
        gpt_command=gpt_command,
    )
    await update.message.reply_text(text_to_send, parse_mode="HTML")


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    keyboard = [
        [InlineKeyboardButton("Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton("English", callback_data="set_lang_en")],
        [InlineKeyboardButton("Español", callback_data="set_lang_es")],
        [InlineKeyboardButton("Deutsch", callback_data="set_lang_de")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    prompt = translates["choose_language_prompt"].get(
        language, translates["choose_language_prompt"]["en"]
    )
    await update.message.reply_text(prompt, reply_markup=reply_markup)


async def lang_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    query = update.callback_query
    await query.answer()

    lang_code = query.data.split("_")[-1]

    if is_private_chat(update):
        chat_id = f"{const.CHAT_PREFIX_USER}{query.from_user.id}"
    else:
        chat_id = f"{const.CHAT_PREFIX_GROUP}{query.message.chat.id}"

    await query.edit_message_text(text=translates["choose_my_language"][lang_code])
    await set_chat_language(chat_id, lang_code)


async def enter_your_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return ConversationHandler.END

    await update.message.reply_text("Please enter your command for GPT:")
    return WAITING_FOR_COMMAND


async def handle_command_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_chat_id(update)
    gpt_command = update.message.text
    await set_gpt_command(chat_id, gpt_command)
    await update.message.reply_text(f"Your command '{gpt_command}' has been saved.")
    return ConversationHandler.END


async def connect_github(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    device_info = await get_github_device_code()
    if "error" in device_info:
        text = translates["github_auth_failed"].get(
            language, translates["github_auth_failed"]["en"]
        )
        await reply_text(update, text)
        logger.error("GitHub device code error: %s", device_info)
        return

    verification_uri = device_info["verification_uri"]
    user_code = device_info["user_code"]
    expires_in = device_info["expires_in"]
    interval = device_info["interval"]

    text = (
        translates["github_auth_prompt"]
        .get(language, translates["github_auth_prompt"]["en"])
        .format(
            verification_uri=verification_uri,
            user_code=user_code,
            expires_in=expires_in,
        )
    )
    await reply_text(update, text)

    async def _poll_and_setup():
        token = await poll_github_for_token(
            device_code=device_info["device_code"],
            interval=interval,
            expires_in=expires_in,
        )
        if not token:
            text = translates["github_auth_timeout"].get(
                language, translates["github_auth_timeout"]["en"]
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
            )
            return

        repo_info = await get_or_create_obsidian_repo(token)
        if not repo_info:
            text = translates["github_repo_failed"].get(
                language, translates["github_repo_failed"]["en"]
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
            )
            return

        await set_github_settings(
            chat_id, repo_info["owner"], repo_info["repo"], repo_info["token"]
        )
        await set_save_to_obsidian(chat_id, True)

        text = (
            translates["github_connected"]
            .get(language, translates["github_connected"]["en"])
            .format(
                owner=repo_info["owner"],
                repo=repo_info["repo"],
            )
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
        )

    task = asyncio.create_task(_poll_and_setup())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def toggle_obsidian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    current = await get_save_to_obsidian(chat_id)
    new_value = not current
    await set_save_to_obsidian(chat_id, new_value)

    language = await get_chat_language(chat_id)
    key = "obsidian_sync_enabled" if new_value else "obsidian_sync_disabled"
    await reply_text(update, translates[key].get(language, translates[key]["en"]))


async def disconnect_github(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    await clear_github_settings(chat_id)
    language = await get_chat_language(chat_id)
    await reply_text(
        update,
        translates["github_disconnected"].get(language, translates["github_disconnected"]["en"]),
    )


async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    credits = await get_total_credits(user_id)
    tier = await get_user_tier(user_id)

    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    total_transcriptions = record.total_transcriptions if record else 0
    total_tokens_used = record.total_tokens_used if record else 0
    total_purchased = record.total_credits_purchased if record else 0

    text = (
        translates["mystats_message"]
        .get(language, translates["mystats_message"]["en"])
        .format(
            credits=credits,
            tier=tier.value,
            total_transcriptions=total_transcriptions,
            total_tokens_used=total_tokens_used,
            total_purchased=total_purchased,
        )
    )
    await reply_text(update, text, parse_mode="HTML")


async def toggle_categorize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    current = await get_auto_categorize(chat_id)
    new_value = not current
    await set_auto_categorize(chat_id, new_value)

    key = "categorize_enabled" if new_value else "categorize_disabled"
    text = translates[key].get(language, translates[key]["en"])
    await reply_text(update, text)


async def toggle_cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    current = await get_auto_cleanup(chat_id)
    new_value = not current
    await set_auto_cleanup(chat_id, new_value)

    key = "cleanup_enabled" if new_value else "cleanup_disabled"
    text = translates[key].get(language, translates[key]["en"])
    await reply_text(update, text)


async def categorize_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    github_settings = await get_github_settings(chat_id)

    if not github_settings:
        text = translates["github_not_connected"].get(
            language, translates["github_not_connected"]["en"]
        )
        await reply_text(update, text)
        return

    count = await categorize_all_income(
        token=github_settings["token"],
        owner=github_settings["owner"],
        repo=github_settings["repo"],
    )

    if count > 0:
        text = translates["categorize_done"].get(language, translates["categorize_done"]["en"])
        await reply_text(update, text.format(count=count))
    else:
        text = translates["categorize_no_files"].get(
            language, translates["categorize_no_files"]["en"]
        )
        await reply_text(update, text)


async def link_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private_chat(update):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    user_id = str(update.effective_user.id)
    code = await generate_link_code(user_id)

    text = (
        translates["whatsapp_link_prompt"]
        .get(language, translates["whatsapp_link_prompt"]["en"])
        .format(code=code)
    )
    await reply_text(update, text)


async def unlink_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private_chat(update):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    user_id = str(update.effective_user.id)
    result = await unlink(user_id)

    if result:
        await reply_text(
            update,
            translates["whatsapp_unlinked"].get(language, translates["whatsapp_unlinked"]["en"]),
        )
    else:
        await reply_text(
            update,
            translates["whatsapp_not_linked"].get(
                language, translates["whatsapp_not_linked"]["en"]
            ),
        )


def _provider_icon(name: str, keys: dict[str, bool]) -> str:
    """Return ✅/❌ based on whether the provider has a key configured."""
    return "✅" if keys.get(name) else "❌"


def _provider_rpm(name: str) -> str:
    rpm = _PROVIDER_LIMITS.get(name)
    return f" {rpm}rpm" if rpm else ""


async def build_stats_text() -> str:
    """Build admin stats message text."""
    month = current_month_key()
    stats = await get_monthly_stats(month)
    wit_limit = settings.wit_free_monthly_limit
    wit_usage_by_lang = await get_all_wit_usage_this_month()

    total_transcriptions = stats.total_transcriptions if stats else 0
    total_payments = stats.total_payments if stats else 0
    total_credits_sold = stats.total_credits_sold if stats else 0
    groq_audio_seconds = stats.groq_audio_seconds if stats else 0

    revenue = total_credits_sold * const.STAR_TO_DOLLAR
    groq_cost = groq_audio_seconds / 3600 * 0.04

    def _wit_status(usage: int) -> str:
        if usage >= wit_limit * 0.95:
            return "CRITICAL"
        if usage >= wit_limit * 0.8:
            return "Warning"
        return "OK"

    # LLM provider key status
    keys: dict[str, bool] = {
        const.PROVIDER_GROQ: bool(settings.groq_api_key),
        const.PROVIDER_GEMINI: bool(settings.gemini_api_key),
        const.PROVIDER_ANTHROPIC: bool(settings.anthropic_bot_api_key),
        const.PROVIDER_OPENROUTER: bool(settings.openrouter_api_key),
        const.PROVIDER_OPENAI: bool(settings.gpt_token),
    }

    def _chain_str(primary: str, fallback_chain: list[str]) -> str:
        chain = [primary] + [p for p in fallback_chain if p != primary]
        parts = [f"{p}{_provider_rpm(p)} {_provider_icon(p, keys)}" for p in chain]
        return " → ".join(parts)

    categ_primary = await get_bot_config(
        "categorization_provider", settings.categorization_provider
    )
    gpt_primary = await get_bot_config("gpt_provider", settings.gpt_provider)
    categ_chain = _chain_str(categ_primary, CATEGORIZATION_FALLBACK_CHAIN)
    gpt_chain = _chain_str(gpt_primary, GPT_FALLBACK_CHAIN)

    # Providers with keys that are not part of any active chain
    all_chain_providers = set(CATEGORIZATION_FALLBACK_CHAIN) | set(GPT_FALLBACK_CHAIN)
    unused_with_key = [p for p, has_key in keys.items() if has_key and p not in all_chain_providers]
    unused_line = f"\n• Not in chain: {', '.join(unused_with_key)}" if unused_with_key else ""

    return (
        f"📊 <b>System Stats ({month})</b>\n\n"
        f"<b>Users</b>\n"
        f"• Total transcriptions: {total_transcriptions:,}\n"
        f"• Payments: {total_payments}\n\n"
        f"<b>Revenue</b>\n"
        f"• Stars received: {total_credits_sold}★\n"
        f"• Credits sold: {total_credits_sold}\n"
        f"• Revenue: ${revenue:.2f}\n\n"
        f"<b>Costs</b>\n"
        f"• Wit.ai / {wit_limit:,} req/mo:\n"
        + "".join(
            f"  - {lang}: {usage:,} ({usage / wit_limit * 100:.1f}%)\n"
            for lang, usage in sorted(wit_usage_by_lang.items())
        )
        + ("  - (no data yet)\n" if not wit_usage_by_lang else "")
        + f"• Groq audio: {groq_audio_seconds} sec/mo (${groq_cost:.2f})"
        f" | limit: {settings.groq_audio_daily_limit:,} sec/day\n\n"
        f"<b>LLM Providers</b>\n"
        f"• Categ: {categ_chain}\n"
        f"• GPT:   {gpt_chain}"
        f"{unused_line}\n\n"
        f"<b>Health</b>\n"
        + "".join(
            f"• Wit.ai ({lang}): "
            f"{'✅' if _wit_status(u) == 'OK' else '⚠️' if _wit_status(u) == 'Warning' else '🚨'} "
            f"{_wit_status(u)}\n"
            for lang, u in sorted(wit_usage_by_lang.items())
        )
        + ("• Wit.ai: ✅ OK (no data)\n" if not wit_usage_by_lang else "")
        + f"• Groq: {'✅' if settings.groq_api_key else '❌'} "
        f"{'Configured' if settings.groq_api_key else 'Not configured'}"
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(str(update.effective_user.id)):
        return
    text = await build_stats_text()
    await update.message.reply_text(text, parse_mode="HTML")


async def settings_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    keyboard = [
        [InlineKeyboardButton(translates["btn_language"][language], callback_data="hub_language")],
        [
            InlineKeyboardButton(
                translates["btn_gpt_command"][language], callback_data="hub_gpt_command"
            )
        ],
    ]

    # Show paid-tier options
    if update.effective_user:
        user_id = str(update.effective_user.id)
        tier = await get_user_tier(user_id)
        if tier not in (UserTier.FREE,):
            # Provider selection (when multiple providers available)
            if settings.groq_api_key:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            translates["btn_provider"][language], callback_data="hub_provider"
                        )
                    ]
                )

            # Transcript cleanup toggle
            cleanup_on = await get_auto_cleanup(chat_id)
            cleanup_key = "btn_toggle_cleanup_on" if cleanup_on else "btn_toggle_cleanup_off"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        translates[cleanup_key][language], callback_data="hub_toggle_cleanup"
                    )
                ]
            )

    reply_markup = InlineKeyboardMarkup(keyboard)
    title = translates["settings_hub_title"][language]
    await update.message.reply_text(title, reply_markup=reply_markup)


async def obsidian_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    github_settings = await get_github_settings(chat_id)

    if not github_settings:
        keyboard = [
            [
                InlineKeyboardButton(
                    translates["btn_connect_github"][language], callback_data="hub_connect_github"
                )
            ],
        ]
    else:
        sync_on = await get_save_to_obsidian(chat_id)
        sort_on = await get_auto_categorize(chat_id)

        sync_label = translates["btn_toggle_sync_on" if sync_on else "btn_toggle_sync_off"][
            language
        ]
        sort_label = translates["btn_toggle_sort_on" if sort_on else "btn_toggle_sort_off"][
            language
        ]

        keyboard = [
            [InlineKeyboardButton(sync_label, callback_data="hub_toggle_obsidian")],
            [InlineKeyboardButton(sort_label, callback_data="hub_toggle_categorize")],
            [
                InlineKeyboardButton(
                    translates["btn_categorize_all"][language], callback_data="hub_categorize"
                )
            ],
            [
                InlineKeyboardButton(
                    translates["btn_setup_obsidian_git"][language],
                    callback_data="hub_setup_obsidian_git",
                )
            ],
            [
                InlineKeyboardButton(
                    translates["btn_disconnect_github"][language],
                    callback_data="hub_disconnect_github",
                )
            ],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if github_settings:
        title = translates["obsidian_hub_connected"][language].format(
            owner=github_settings["owner"],
            repo=github_settings["repo"],
        )
    else:
        title = translates["obsidian_hub_title"][language]
    await update.message.reply_text(title, reply_markup=reply_markup, parse_mode="HTML")


async def account_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private_chat(update):
        return

    chat_id = get_chat_id(update)
    user_id = str(update.effective_user.id)
    language = await get_chat_language(chat_id)

    whatsapp_linked = await get_linked_whatsapp(user_id)

    keyboard = [
        [InlineKeyboardButton(translates["btn_buy"][language], callback_data="hub_buy")],
        [InlineKeyboardButton(translates["btn_balance"][language], callback_data="hub_balance")],
        [InlineKeyboardButton(translates["btn_mystats"][language], callback_data="hub_mystats")],
    ]

    if whatsapp_linked:
        keyboard.append(
            [
                InlineKeyboardButton(
                    translates["btn_unlink_whatsapp"][language], callback_data="hub_unlink_whatsapp"
                )
            ]
        )
    else:
        keyboard.append(
            [
                InlineKeyboardButton(
                    translates["btn_link_whatsapp"][language], callback_data="hub_link_whatsapp"
                )
            ]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    title = translates["account_hub_title"][language]
    await update.message.reply_text(title, reply_markup=reply_markup)


async def _show_provider_menu(update: Update):
    query = update.callback_query
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    current = await get_preferred_provider(chat_id)

    prompt = translates["choose_provider_prompt"].get(
        language, translates["choose_provider_prompt"]["en"]
    )

    check = "\u2705 "
    keyboard = [
        [
            InlineKeyboardButton(
                f"{check if current is None else ''}Auto",
                callback_data="set_prov_auto",
            )
        ],
        [
            InlineKeyboardButton(
                f"{check if current == const.PROVIDER_WIT else ''}Wit.ai",
                callback_data="set_prov_wit",
            )
        ],
    ]
    if settings.groq_api_key:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{check if current == const.PROVIDER_GROQ else ''}Groq",
                    callback_data="set_prov_groq",
                )
            ]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(prompt, reply_markup=reply_markup)


async def _hub_show_language_menu(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    prompt = translates["choose_language_prompt"].get(
        language, translates["choose_language_prompt"]["en"]
    )

    keyboard = [
        [InlineKeyboardButton("Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton("English", callback_data="set_lang_en")],
        [InlineKeyboardButton("Español", callback_data="set_lang_es")],
        [InlineKeyboardButton("Deutsch", callback_data="set_lang_de")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(prompt, reply_markup=reply_markup)


async def _hub_show_provider(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await _show_provider_menu(update)


async def setup_obsidian_git(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    github_settings = await get_github_settings(chat_id)
    if not github_settings:
        await query.edit_message_text(translates["github_not_connected"][language])
        return
    success = await create_obsidian_git_config(
        token=github_settings["token"],
        owner=github_settings["owner"],
        repo=github_settings["repo"],
    )
    key = "obsidian_git_setup_done" if success else "obsidian_git_setup_failed"
    await query.answer(translates[key][language], show_alert=True)


_HUB_ACTIONS = {
    "language": _hub_show_language_menu,
    "buy": buy_command,
    "balance": balance_command,
    "mystats": mystats_command,
    "toggle_obsidian": toggle_obsidian,
    "toggle_categorize": toggle_categorize,
    "toggle_cleanup": toggle_cleanup,
    "categorize": categorize_all,
    "setup_obsidian_git": setup_obsidian_git,
    "connect_github": connect_github,
    "disconnect_github": disconnect_github,
    "link_whatsapp": link_whatsapp,
    "unlink_whatsapp": unlink_whatsapp,
    "provider": _hub_show_provider,
}


async def hub_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data.replace("hub_", "")
    handler = _HUB_ACTIONS.get(action)
    if handler:
        await handler(update, context)


async def provider_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    query = update.callback_query
    await query.answer()

    choice = query.data.replace("set_prov_", "")

    if is_private_chat(update):
        chat_id = f"{const.CHAT_PREFIX_USER}{query.from_user.id}"
    else:
        chat_id = f"{const.CHAT_PREFIX_GROUP}{query.message.chat.id}"

    language = await get_chat_language(chat_id)

    provider_map = {
        "auto": (None, "choose_my_provider_auto"),
        "wit": (const.PROVIDER_WIT, "choose_my_provider_wit"),
        "groq": (const.PROVIDER_GROQ, "choose_my_provider_groq"),
    }

    provider_value, translate_key = provider_map.get(choice, (None, "choose_my_provider_auto"))
    await set_preferred_provider(chat_id, provider_value)
    await query.edit_message_text(
        text=translates[translate_key].get(language, translates[translate_key]["en"])
    )


async def enter_your_command_from_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Please enter your command for GPT:")
    return WAITING_FOR_COMMAND
