"""
Top-level dispatcher for non-command messages in group chats.

A single handler is registered for group/supergroup messages so we have
full, explicit control over the order admin commands vs. ordinary player
content are checked, rather than relying on python-telegram-bot's
handler-group ordering (which is fragile for this kind of either/or logic).
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from handlers.admin import handle_admin_reply_command
from handlers.player import handle_player_message


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    config = context.bot_data["config"]

    if user.id == config.admin_user_id:
        if message.reply_to_message is not None and message.text:
            await handle_admin_reply_command(update, context)
        # Any other admin message in a player's group (not a recognized
        # reply-command) is an off-the-record note and is ignored - only
        # the tracked player's own messages are ever published.
        return

    await handle_player_message(update, context)
