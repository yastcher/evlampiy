import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from src import const
from src.account_linking import generate_link_code, get_linked_whatsapp, unlink
from src.categorization import categorize_all_income
from src.config import settings
from src.credits import (
    current_month_key,
    get_credits,
    get_monthly_stats,
    get_user_tier,
    is_admin_user,
)
from src.dto import UserCredits
from src.github_api import get_or_create_obsidian_repo
from src.github_oauth import get_github_device_code, poll_github_for_token
from src.localization import translates
from src.mongo import (
    clear_github_settings,
    get_auto_categorize,
    get_chat_language,
    get_github_settings,
    get_gpt_command,
    get_save_to_obsidian,
    set_auto_categorize,
    set_chat_language,
    set_github_settings,
    set_gpt_command,
    set_save_to_obsidian,
)
from src.telegram.chat_params import get_chat_id, is_private_chat, is_user_admin, reply_text
from src.telegram.payments import balance_command, buy_command
from src.wit_tracking import get_wit_usage_this_month

logger = logging.getLogger(__name__)

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
    prompt = translates["choose_language_prompt"].get(language, translates["choose_language_prompt"]["en"])
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
        text = translates["github_auth_failed"].get(language, translates["github_auth_failed"]["en"])
        await reply_text(update, text)
        logger.error("GitHub device code error: %s", device_info)
        return

    verification_uri = device_info["verification_uri"]
    user_code = device_info["user_code"]
    expires_in = device_info["expires_in"]
    interval = device_info["interval"]

    text = translates["github_auth_prompt"].get(language, translates["github_auth_prompt"]["en"]).format(
        verification_uri=verification_uri,
        user_code=user_code,
        expires_in=expires_in,
    )
    await reply_text(update, text)

    async def _poll_and_setup():
        token = await poll_github_for_token(
            device_code=device_info["device_code"],
            interval=interval,
            expires_in=expires_in,
        )
        if not token:
            text = translates["github_auth_timeout"].get(language, translates["github_auth_timeout"]["en"])
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
            )
            return

        repo_info = await get_or_create_obsidian_repo(token)
        if not repo_info:
            text = translates["github_repo_failed"].get(language, translates["github_repo_failed"]["en"])
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
            )
            return

        await set_github_settings(
            chat_id, repo_info["owner"], repo_info["repo"], repo_info["token"]
        )
        await set_save_to_obsidian(chat_id, True)

        text = translates["github_connected"].get(language, translates["github_connected"]["en"]).format(
            owner=repo_info["owner"],
            repo=repo_info["repo"],
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
        )

    asyncio.create_task(_poll_and_setup())


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
    await reply_text(update, translates["github_disconnected"].get(language, translates["github_disconnected"]["en"]))


async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    credits = await get_credits(user_id)
    tier = await get_user_tier(user_id)

    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    total_transcriptions = record.total_transcriptions if record else 0
    total_spent = record.total_credits_spent if record else 0
    total_purchased = record.total_credits_purchased if record else 0

    text = (
        translates["mystats_message"]
        .get(language, translates["mystats_message"]["en"])
        .format(
            credits=credits,
            tier=tier.value,
            total_transcriptions=total_transcriptions,
            total_spent=total_spent,
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


async def categorize_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    github_settings = await get_github_settings(chat_id)

    if not github_settings:
        text = translates["github_not_connected"].get(language, translates["github_not_connected"]["en"])
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

    text = translates["whatsapp_link_prompt"].get(language, translates["whatsapp_link_prompt"]["en"]).format(code=code)
    await reply_text(update, text)


async def unlink_whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private_chat(update):
        return

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    user_id = str(update.effective_user.id)
    result = await unlink(user_id)

    if result:
        await reply_text(update, translates["whatsapp_unlinked"].get(language, translates["whatsapp_unlinked"]["en"]))
    else:
        await reply_text(update, translates["whatsapp_not_linked"].get(language, translates["whatsapp_not_linked"]["en"]))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(str(update.effective_user.id)):
        return

    month = current_month_key()
    stats = await get_monthly_stats(month)
    wit_usage = await get_wit_usage_this_month()
    wit_limit = settings.wit_free_monthly_limit

    total_transcriptions = stats.total_transcriptions if stats else 0
    total_payments = stats.total_payments if stats else 0
    total_credits_sold = stats.total_credits_sold if stats else 0
    groq_audio_seconds = stats.groq_audio_seconds if stats else 0

    revenue = total_credits_sold * const.STAR_TO_DOLLAR
    groq_cost = groq_audio_seconds / 3600 * 0.04

    wit_status = (
        "OK"
        if wit_usage < wit_limit * 0.8
        else ("Warning" if wit_usage < wit_limit * 0.95 else "CRITICAL")
    )
    groq_status = "Configured" if settings.groq_api_key else "Not configured"

    text = (
        f"📊 <b>System Stats ({month})</b>\n\n"
        f"<b>Users</b>\n"
        f"• Total transcriptions: {total_transcriptions:,}\n"
        f"• Payments: {total_payments}\n\n"
        f"<b>Revenue</b>\n"
        f"• Stars received: {total_credits_sold}★\n"
        f"• Credits sold: {total_credits_sold}\n"
        f"• Revenue: ${revenue:.2f}\n\n"
        f"<b>Costs</b>\n"
        f"• Wit.ai: {wit_usage:,} / {wit_limit:,} ({wit_usage / wit_limit * 100:.1f}%)\n"
        f"• Groq: {groq_audio_seconds} sec (${groq_cost:.2f})\n\n"
        f"<b>Health</b>\n"
        f"• Wit.ai: {'✅' if wit_status == 'OK' else '⚠️' if wit_status == 'Warning' else '🚨'} {wit_status}\n"
        f"• Groq: {'✅' if settings.groq_api_key else '❌'} {groq_status}"
    )
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
                    translates["btn_disconnect_github"][language],
                    callback_data="hub_disconnect_github",
                )
            ],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    title = translates["obsidian_hub_title"][language]
    await update.message.reply_text(title, reply_markup=reply_markup)


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


async def hub_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data.replace("hub_", "")

    if action == "language":
        chat_id = get_chat_id(update)
        language = await get_chat_language(chat_id)
        prompt = translates["choose_language_prompt"].get(language, translates["choose_language_prompt"]["en"])

        keyboard = [
            [InlineKeyboardButton("Русский", callback_data="set_lang_ru")],
            [InlineKeyboardButton("English", callback_data="set_lang_en")],
            [InlineKeyboardButton("Español", callback_data="set_lang_es")],
            [InlineKeyboardButton("Deutsch", callback_data="set_lang_de")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(prompt, reply_markup=reply_markup)

    elif action == "buy":
        await buy_command(update, context)

    elif action == "balance":
        await balance_command(update, context)

    elif action == "mystats":
        await mystats_command(update, context)

    elif action == "toggle_obsidian":
        await toggle_obsidian(update, context)

    elif action == "toggle_categorize":
        await toggle_categorize(update, context)

    elif action == "categorize":
        await categorize_all(update, context)

    elif action == "connect_github":
        await connect_github(update, context)

    elif action == "disconnect_github":
        await disconnect_github(update, context)

    elif action == "link_whatsapp":
        await link_whatsapp(update, context)

    elif action == "unlink_whatsapp":
        await unlink_whatsapp(update, context)


async def enter_your_command_from_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Please enter your command for GPT:")
    return WAITING_FOR_COMMAND
