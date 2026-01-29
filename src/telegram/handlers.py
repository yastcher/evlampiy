import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from src import const
from src.chat_params import get_chat_id, is_private_chat, is_user_admin
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
    get_chat_language,
    get_gpt_command,
    get_save_to_obsidian,
    set_chat_language,
    set_github_settings,
    set_gpt_command,
    set_save_to_obsidian,
)
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
    await update.message.reply_text(text_to_send)


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    keyboard = [
        [InlineKeyboardButton("Русский", callback_data="set_lang_ru")],
        [InlineKeyboardButton("English", callback_data="set_lang_en")],
        [InlineKeyboardButton("Español", callback_data="set_lang_es")],
        [InlineKeyboardButton("Deutsch", callback_data="set_lang_de")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please choose your preferred language:",
        reply_markup=reply_markup,
    )


async def lang_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    query = update.callback_query
    await query.answer()

    lang_code = query.data.split("_")[-1]

    if is_private_chat(update):
        chat_id = f"u_{query.from_user.id}"
    else:
        chat_id = f"g_{query.message.chat.id}"

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

    device_info = await get_github_device_code()
    if "error" in device_info:
        await update.message.reply_text("Failed to start GitHub authorization.")
        logger.error("GitHub device code error: %s", device_info)
        return

    verification_uri = device_info["verification_uri"]
    user_code = device_info["user_code"]
    expires_in = device_info["expires_in"]
    interval = device_info["interval"]

    await update.message.reply_text(
        f"1) Open: {verification_uri}\n"
        f"2) Enter code: {user_code}\n\n"
        f"You have {expires_in} seconds to complete authorization."
    )

    async def _poll_and_setup():
        token = await poll_github_for_token(
            device_code=device_info["device_code"],
            interval=interval,
            expires_in=expires_in,
        )
        if not token:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="GitHub authorization failed or timed out. Try /connect_github again.",
            )
            return

        repo_info = await get_or_create_obsidian_repo(token)
        if not repo_info:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Failed to create/access GitHub repository.",
            )
            return

        await set_github_settings(
            chat_id, repo_info["owner"], repo_info["repo"], repo_info["token"]
        )
        await set_save_to_obsidian(chat_id, True)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"GitHub connected! Repository: {repo_info['owner']}/{repo_info['repo']}\n"
                "Obsidian sync is now enabled."
            ),
        )

    asyncio.create_task(_poll_and_setup())


async def toggle_obsidian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    current = await get_save_to_obsidian(chat_id)
    new_value = not current
    await set_save_to_obsidian(chat_id, new_value)

    status = "enabled" if new_value else "disabled"
    await update.message.reply_text(f"Obsidian sync is now {status}.")


async def disconnect_github(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_admin(update, context):
        return

    chat_id = get_chat_id(update)
    await clear_github_settings(chat_id)
    await update.message.reply_text("GitHub disconnected. Obsidian sync disabled.")


async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)

    credits = await get_credits(user_id)
    tier = await get_user_tier(user_id)

    record = await UserCredits.find_one(UserCredits.user_id == user_id)
    total_transcriptions = record.total_transcriptions if record else 0
    total_spent = record.total_credits_spent if record else 0
    total_purchased = record.total_credits_purchased if record else 0

    text = translates["mystats_message"].get(language, translates["mystats_message"]["en"]).format(
        credits=credits,
        tier=tier.value,
        total_transcriptions=total_transcriptions,
        total_spent=total_spent,
        total_purchased=total_purchased,
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin_user(update.effective_user.id):
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

    wit_status = "OK" if wit_usage < wit_limit * 0.8 else ("Warning" if wit_usage < wit_limit * 0.95 else "CRITICAL")
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
        f"• Wit.ai: {wit_usage:,} / {wit_limit:,} ({wit_usage/wit_limit*100:.1f}%)\n"
        f"• Groq: {groq_audio_seconds} sec (${groq_cost:.2f})\n\n"
        f"<b>Health</b>\n"
        f"• Wit.ai: {'✅' if wit_status == 'OK' else '⚠️' if wit_status == 'Warning' else '🚨'} {wit_status}\n"
        f"• Groq: {'✅' if settings.groq_api_key else '❌'} {groq_status}"
    )
    await update.message.reply_text(text, parse_mode="HTML")
