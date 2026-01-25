"""Telegram voice message handler."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.chat_params import get_chat_id
from src.mongo import get_chat_language, get_gpt_command
from src.telegram.bot import send_response
from src.transcription.service import transcribe_audio

logger = logging.getLogger(__name__)


async def from_voice_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice message from Telegram."""
    if not update.message.voice:
        return

    voice_file = await update.message.voice.get_file()
    file_data = await voice_file.download_as_bytearray()

    chat_id = get_chat_id(update)
    language = await get_chat_language(chat_id)
    gpt_command = await get_gpt_command(chat_id)

    text = transcribe_audio(bytes(file_data), audio_format="ogg", language=language)

    logger.debug("Voice message translation: %s", text)
    if not text:
        logger.debug("Empty voice message.")
        return

    if text.lower().startswith(gpt_command):
        response_kwargs = {
            "response": f"Command \\*{gpt_command}* detected in the voice message."
            f"\nAsk GPT for: {text[len(gpt_command) :]}"
        }
    else:
        response_kwargs = {
            "response": text,
            "reply_to_message_id": update.message.message_id,
        }

    await send_response(update, context, **response_kwargs)
