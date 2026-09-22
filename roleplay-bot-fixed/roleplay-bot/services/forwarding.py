"""
Formats and sends player messages to the public Roleplay channel.

Uses copy_message (not forward_message) so that:
  - there is no "Forwarded from" attribution on the channel post, and
  - the caption/text can be fully replaced with our roleplay-identity header
    while Telegram still handles the underlying photo file server-side
    (no download/re-upload needed).
"""

from __future__ import annotations

import logging
from typing import Optional

from telegram import Bot

from constants import CHANNEL_TEMPLATE, MAX_CAPTION_LENGTH, MAX_MESSAGE_LENGTH, NO_USERNAME_TEXT

logger = logging.getLogger(__name__)


def _username_display(username: Optional[str]) -> str:
    return f"@{username}" if username else NO_USERNAME_TEXT


def build_header(
    game_name: str,
    country: str,
    display_name: str,
    username: Optional[str],
    telegram_user_id: int,
) -> str:
    return CHANNEL_TEMPLATE.format(
        game_name=game_name,
        country=country,
        display_name=display_name,
        username_display=_username_display(username),
        telegram_user_id=telegram_user_id,
        content="",
    ).rstrip()


async def forward_text(bot: Bot, channel_id: str, header: str, text: str) -> int:
    """Send a text-only roleplay message to the channel. Returns the channel_message_id."""
    full_text = f"{header}\n\n{text}"
    if len(full_text) > MAX_MESSAGE_LENGTH:
        # Telegram's hard limit for message text - trim the player's content only,
        # never the identity header.
        overflow = len(full_text) - MAX_MESSAGE_LENGTH
        text = text[: max(0, len(text) - overflow - 20)] + "… (truncated)"
        full_text = f"{header}\n\n{text}"

    sent = await bot.send_message(chat_id=channel_id, text=full_text)
    return sent.message_id


async def forward_photo(
    bot: Bot,
    channel_id: str,
    source_chat_id: int,
    source_message_id: int,
    header: str,
    caption: Optional[str],
) -> int:
    """
    Copy a photo message (with optional caption) to the channel.
    Returns the channel_message_id.
    """
    caption = caption or ""
    combined = f"{header}\n\n{caption}".rstrip() if caption else header

    if len(combined) <= MAX_CAPTION_LENGTH:
        result = await bot.copy_message(
            chat_id=channel_id,
            from_chat_id=source_chat_id,
            message_id=source_message_id,
            caption=combined,
        )
        return result.message_id

    # Telegram caps photo captions at 1024 characters (vs. 4096 for plain
    # text messages). Rather than silently truncating the player's caption,
    # post the photo with just the identity header, then send the full
    # original caption as a separate follow-up text message.
    logger.info("Caption too long for photo (%d chars); splitting into two messages.", len(combined))
    result = await bot.copy_message(
        chat_id=channel_id,
        from_chat_id=source_chat_id,
        message_id=source_message_id,
        caption=header,
    )
    await bot.send_message(chat_id=channel_id, text=caption)
    return result.message_id
