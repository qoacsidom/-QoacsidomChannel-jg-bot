"""Data access for players, game memberships (game_players), and chat linking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import aiosqlite


@dataclass
class GamePlayerRecord:
    """A player's membership in one specific game (one row per game+player)."""

    id: int
    game_id: int
    player_id: int
    telegram_user_id: int
    display_name: str
    country_or_faction: str
    active: bool
    private_chat_id: Optional[int]
    game_name: str = ""

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "GamePlayerRecord":
        keys = row.keys()
        return cls(
            id=row["id"],
            game_id=row["game_id"],
            player_id=row["player_id"],
            telegram_user_id=row["telegram_user_id"],
            display_name=row["display_name"],
            country_or_faction=row["country_or_faction"],
            active=bool(row["active"]),
            private_chat_id=row["private_chat_id"],
            game_name=row["game_name"] if "game_name" in keys else "",
        )


# NOTE: game_players has no telegram_user_id column - it lives on `players`.
# Every query that builds a GamePlayerRecord must therefore join `players`
# and select p.telegram_user_id explicitly.
_SELECT_WITH_GAME_NAME = """
    SELECT gp.*, p.telegram_user_id AS telegram_user_id, g.name AS game_name
    FROM game_players gp
    JOIN games g ON g.id = gp.game_id
    JOIN players p ON p.id = gp.player_id
"""


class PlayerRepository:
    def __init__(self, connection: aiosqlite.Connection):
        self._conn = connection

    # -- players ------------------------------------------------------
    async def get_or_create_player(self, telegram_user_id: int, username: Optional[str]) -> int:
        cursor = await self._conn.execute(
            "SELECT id FROM players WHERE telegram_user_id = ?", (telegram_user_id,)
        )
        row = await cursor.fetchone()
        if row:
            await self.update_username(telegram_user_id, username)
            return row["id"]

        cursor = await self._conn.execute(
            "INSERT INTO players (telegram_user_id, telegram_username) VALUES (?, ?)",
            (telegram_user_id, username),
        )
        await self._conn.commit()
        return cursor.lastrowid

    async def update_username(self, telegram_user_id: int, username: Optional[str]) -> None:
        await self._conn.execute(
            "UPDATE players SET telegram_username = ?, updated_at = datetime('now') "
            "WHERE telegram_user_id = ?",
            (username, telegram_user_id),
        )
        await self._conn.commit()

    # -- pending chat senders (used before a chat is linked to a game) --
    async def record_pending_sender(
        self, private_chat_id: int, telegram_user_id: int, username: Optional[str]
    ) -> None:
        await self._conn.execute(
            """
            INSERT INTO pending_chat_senders (private_chat_id, telegram_user_id, telegram_username, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(private_chat_id) DO UPDATE SET
                telegram_user_id = excluded.telegram_user_id,
                telegram_username = excluded.telegram_username,
                updated_at = excluded.updated_at
            """,
            (private_chat_id, telegram_user_id, username),
        )
        await self._conn.commit()

    async def get_pending_sender(self, private_chat_id: int) -> Optional[aiosqlite.Row]:
        cursor = await self._conn.execute(
            "SELECT * FROM pending_chat_senders WHERE private_chat_id = ?", (private_chat_id,)
        )
        return await cursor.fetchone()

    async def clear_pending_sender(self, private_chat_id: int) -> None:
        await self._conn.execute(
            "DELETE FROM pending_chat_senders WHERE private_chat_id = ?", (private_chat_id,)
        )
        await self._conn.commit()

    # -- game_players ---------------------------------------------------
    async def link_chat_to_game(
        self, private_chat_id: int, game_id: int, telegram_user_id: int, username: Optional[str]
    ) -> GamePlayerRecord:
        player_id = await self.get_or_create_player(telegram_user_id, username)
        cursor = await self._conn.execute(
            """
            INSERT INTO game_players (game_id, player_id, private_chat_id, display_name, country_or_faction)
            VALUES (?, ?, ?, '', '')
            """,
            (game_id, player_id, private_chat_id),
        )
        await self._conn.commit()
        record = await self.get_by_id(cursor.lastrowid)
        assert record is not None
        return record

    async def get_by_id(self, game_player_id: int) -> Optional[GamePlayerRecord]:
        cursor = await self._conn.execute(
            f"{_SELECT_WITH_GAME_NAME} WHERE gp.id = ?", (game_player_id,)
        )
        row = await cursor.fetchone()
        return GamePlayerRecord.from_row(row) if row else None

    async def get_by_chat(self, private_chat_id: int) -> Optional[GamePlayerRecord]:
        cursor = await self._conn.execute(
            f"{_SELECT_WITH_GAME_NAME} WHERE gp.private_chat_id = ?", (private_chat_id,)
        )
        row = await cursor.fetchone()
        return GamePlayerRecord.from_row(row) if row else None

    async def find_membership(self, game_id: int, telegram_user_id: int) -> Optional[GamePlayerRecord]:
        """Look up whether a Telegram user already belongs to a given game (in any chat)."""
        cursor = await self._conn.execute(
            f"{_SELECT_WITH_GAME_NAME} WHERE gp.game_id = ? AND p.telegram_user_id = ?",
            (game_id, telegram_user_id),
        )
        row = await cursor.fetchone()
        return GamePlayerRecord.from_row(row) if row else None

    async def is_game_active(self, game_id: int) -> bool:
        cursor = await self._conn.execute("SELECT active FROM games WHERE id = ?", (game_id,))
        row = await cursor.fetchone()
        return bool(row["active"]) if row else False

    async def update_country(self, game_player_id: int, value: str) -> None:
        await self._conn.execute(
            "UPDATE game_players SET country_or_faction = ?, updated_at = datetime('now') WHERE id = ?",
            (value, game_player_id),
        )
        await self._conn.commit()

    async def update_display_name(self, game_player_id: int, value: str) -> None:
        await self._conn.execute(
            "UPDATE game_players SET display_name = ?, updated_at = datetime('now') WHERE id = ?",
            (value, game_player_id),
        )
        await self._conn.commit()

    async def set_active(self, game_player_id: int, active: bool) -> None:
        await self._conn.execute(
            "UPDATE game_players SET active = ?, updated_at = datetime('now') WHERE id = ?",
            (1 if active else 0, game_player_id),
        )
        await self._conn.commit()

    async def list_by_game(self, game_id: int) -> list[GamePlayerRecord]:
        cursor = await self._conn.execute(
            f"{_SELECT_WITH_GAME_NAME} WHERE gp.game_id = ? ORDER BY gp.id", (game_id,)
        )
        rows = await cursor.fetchall()
        return [GamePlayerRecord.from_row(r) for r in rows]

    async def list_all(self) -> list[GamePlayerRecord]:
        cursor = await self._conn.execute(f"{_SELECT_WITH_GAME_NAME} ORDER BY gp.game_id, gp.id")
        rows = await cursor.fetchall()
        return [GamePlayerRecord.from_row(r) for r in rows]
