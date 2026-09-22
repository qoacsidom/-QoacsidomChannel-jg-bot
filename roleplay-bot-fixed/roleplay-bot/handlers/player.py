"""
Handles messages sent by players inside their private roleplay group, and
forwards authorized, active players' text/photo messages to the public
Roleplay channel.

NOTE: this function assumes the caller (handlers/dispatch.py) has already
confirmed the sender is NOT the admin - admin messages are never treated
as roleplay content, even if they don't match a recognized command.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from constants import (
    MSG_CHANNEL_SEND_FAILED,
    MSG_CHAT_NOT_LINKED,
    MSG_GAME_INACTIVE,
    MSG_PLAYER_INACTIVE,
    MSG_UNKNOWN_SENDER_IN_LINKED_CHAT,
    MSG_UNSUPPORTED_MEDIA,
)
from repositories.messages import MessageRecord
from services import forwarding
from services.tracking import track_potential_sender

logger = logging.getLogger(__name__)


async def handle_player_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if message is None or chat is None or user is None:
        return

    config = context.bot_data["config"]
    player_repo = context.bot_data["player_repo"]
    message_repo = context.bot_data["message_repo"]

    link = await player_repo.get_by_chat(chat.id)

    if link is None:
        await track_potential_sender(context, chat.id, user)
        await message.reply_text(MSG_CHAT_NOT_LINKED)
        return

    if user.id != link.telegram_user_id:
        logger.warning(
            "Ignoring message from unrecognized user_id=%s in chat_id=%s (expected %s).",
            user.id, chat.id, link.telegram_user_id,
        )
        await message.reply_text(MSG_UNKNOWN_SENDER_IN_LINKED_CHAT)
        return

    if not link.active:
        await message.reply_text(MSG_PLAYER_INACTIVE)
        return

    if not await player_repo.is_game_active(link.game_id):
        await message.reply_text(MSG_GAME_INACTIVE)
        return

    await player_repo.update_username(user.id, user.username)

    header = forwarding.build_header(
        game_name=link.game_name,
        country=link.country_or_faction,
        display_name=link.display_name,
        username=user.username,
        telegram_user_id=user.id,
    )

    if message.photo:
        message_type = "photo"
        text_or_caption = message.caption
    elif message.text:
        message_type = "text"
        text_or_caption = message.text
    else:
        await message.reply_text(MSG_UNSUPPORTED_MEDIA)
        return

    try:
        if message_type == "photo":
            channel_message_id = await forwarding.forward_photo(
                bot=context.bot,
                channel_id=config.channel_id,
                source_chat_id=chat.id,
                source_message_id=message.message_id,
                header=header,
                caption=text_or_caption,
            )
        else:
            channel_message_id = await forwarding.forward_text(
                bot=context.bot,
                channel_id=config.channel_id,
                header=header,
                text=text_or_caption,
            )
    except TelegramError as exc:
        logger.error("Failed to forward message to channel %s: %s", config.channel_id, exc)
        await message.reply_text(MSG_CHANNEL_SEND_FAILED)
        return

    record = MessageRecord(
        game_id=link.game_id,
        player_id=link.player_id,
        telegram_user_id=user.id,
        display_name_at_message=link.display_name,
        country_or_faction_at_message=link.country_or_faction,
        telegram_username_at_message=user.username,
        telegram_message_id=message.message_id,
        private_chat_id=chat.id,
        message_type=message_type,
        text_or_caption=text_or_caption,
        channel_message_id=channel_message_id,
    )
    await message_repo.record_message(record)
    logger.info(
        "Forwarded %s message from player_id=%s (game_id=%s) to channel_message_id=%s",
        message_type, link.player_id, link.game_id, channel_message_id,
    )
