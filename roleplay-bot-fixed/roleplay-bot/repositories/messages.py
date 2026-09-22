"""Data access for the immutable `messages` history table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import aiosqlite


@dataclass
class MessageRecord:
    game_id: int
    player_id: int
    telegram_user_id: int
    display_name_at_message: str
    country_or_faction_at_message: str
    telegram_username_at_message: Optional[str]
    telegram_message_id: int
    private_chat_id: int
    message_type: str
    text_or_caption: Optional[str]
    channel_message_id: Optional[int] = None


class MessageRepository:
    def __init__(self, connection: aiosqlite.Connection):
        self._conn = connection

    async def record_message(self, record: MessageRecord) -> int:
        """
        Insert a new, immutable snapshot of a forwarded message.

        IMPORTANT: the identity fields on this row (display_name_at_message,
        country_or_faction_at_message, telegram_username_at_message) must
        NEVER be updated after insertion. This is what guarantees old
        channel posts keep showing the identity the player had *at the
        time*, even after the admin later changes their name/country.
        """
        cursor = await self._conn.execute(
            """
            INSERT INTO messages (
                game_id, player_id, telegram_user_id,
                display_name_at_message, country_or_faction_at_message,
                telegram_username_at_message, telegram_message_id,
                private_chat_id, channel_message_id, message_type, text_or_caption
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.game_id,
                record.player_id,
                record.telegram_user_id,
                record.display_name_at_message,
                record.country_or_faction_at_message,
                record.telegram_username_at_message,
                record.telegram_message_id,
                record.private_chat_id,
                record.channel_message_id,
                record.message_type,
                record.text_or_caption,
            ),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def attach_channel_message_id(self, message_row_id: int, channel_message_id: int) -> None:
        """Attach the channel_message_id after a successful send. Does not touch identity fields."""
        await self._conn.execute(
            "UPDATE messages SET channel_message_id = ? WHERE id = ?",
            (channel_message_id, message_row_id),
        )
        await self._conn.commit()
