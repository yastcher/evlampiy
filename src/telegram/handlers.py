from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from src.chat_params import get_chat_id, is_private_chat, is_user_admin
from src.github_tg_oauth import authorize_github_for_user
from src.localization import translates
from src.mongo import (
    get_chat_language,
    get_gpt_command,
    set_chat_language,
    set_github_settings,
    set_gpt_command,
)

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


async def set_github_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /set_github
    await response: owner repo token
    # /set_github MyUser MyRepo ghp_XXXX...
    """
    chat_id = get_chat_id(update)
    if not update.message or not update.message.text:
        return
    parts = update.message.text.split()
    if len(parts) < 4:
        await update.message.reply_text("Usage: /set_github <owner> <repo> <token>")
        return
    _, owner, repo, token = parts
    await set_github_settings(chat_id, owner, repo, token)
    await update.message.reply_text("GitHub settings saved.")


async def connect_github(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await authorize_github_for_user(update, context)
