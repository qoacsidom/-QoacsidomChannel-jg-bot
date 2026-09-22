"""
Tracks the most recent non-admin sender in group chats that are not yet
linked to a game.

Telegram gives bots no way to resolve a user's numeric ID from just their
@username - a bot only learns a user's ID once it has observed a message
from them. This module records that observation so the admin can later
link the chat to a game and have the right player picked up automatically.
"""

from __future__ import annotations

from telegram import User
from telegram.ext import ContextTypes


async def track_potential_sender(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user: User) -> None:
    config = context.bot_data["config"]
    if user.id == config.admin_user_id:
        return  # the admin's own messages are never treated as a player's

    player_repo = context.bot_data["player_repo"]
    existing_link = await player_repo.get_by_chat(chat_id)
    if existing_link is not None:
        return  # already linked; no need to track a pending sender anymore

    await player_repo.record_pending_sender(chat_id, user.id, user.username)
