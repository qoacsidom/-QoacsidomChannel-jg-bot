"""
Handler for the /start command.

Sending /start never authorizes a player by itself - the admin must
explicitly link a chat to a game (see handlers/admin.py).
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from constants import MSG_START_GENERIC
from services.tracking import track_potential_sender

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    if chat is None or user is None or message is None:
        return

    logger.info("Received /start from user_id=%s in chat_id=%s", user.id, chat.id)

    if chat.type in ("group", "supergroup"):
        await track_potential_sender(context, chat.id, user)

    await message.reply_text(MSG_START_GENERIC)
