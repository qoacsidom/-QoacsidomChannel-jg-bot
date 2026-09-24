"""Data access for the `games` table (plus global persisted bot settings)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import aiosqlite

from constants import DEFAULT_COOLDOWN_SECONDS

_FROZEN_KEY = "channel_frozen"


@dataclass
class Game:
    id: int
    name: str
    active: bool
    created_at: str
    updated_at: str
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Game":
        keys = row.keys()
        return cls(
            id=row["id"],
            name=row["name"],
            active=bool(row["active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            cooldown_seconds=(
                row["cooldown_seconds"] if "cooldown_seconds" in keys else DEFAULT_COOLDOWN_SECONDS
            ),
        )


class GameRepository:
    def __init__(self, connection: aiosqlite.Connection):
        self._conn = connection

    async def create(self, name: str) -> Game:
        cursor = await self._conn.execute("INSERT INTO games (name) VALUES (?)", (name,))
        await self._conn.commit()
        game = await self.get_by_id(cursor.lastrowid)
        assert game is not None
        return game

    async def get_by_id(self, game_id: int) -> Optional[Game]:
        cursor = await self._conn.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        row = await cursor.fetchone()
        return Game.from_row(row) if row else None

    async def list_all(self) -> list[Game]:
        cursor = await self._conn.execute("SELECT * FROM games ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [Game.from_row(r) for r in rows]

    async def list_active(self) -> list[Game]:
        cursor = await self._conn.execute("SELECT * FROM games WHERE active = 1 ORDER BY id DESC")
        rows = await cursor.fetchall()
        return [Game.from_row(r) for r in rows]

    async def set_active(self, game_id: int, active: bool) -> None:
        await self._conn.execute(
            "UPDATE games SET active = ?, updated_at = datetime('now') WHERE id = ?",
            (1 if active else 0, game_id),
        )
        await self._conn.commit()

    # -- anti-spam cooldown (per game) ---------------------------------------
    async def get_cooldown_seconds(self, game_id: int) -> int:
        cursor = await self._conn.execute(
            "SELECT cooldown_seconds FROM games WHERE id = ?", (game_id,)
        )
        row = await cursor.fetchone()
        return int(row["cooldown_seconds"]) if row else DEFAULT_COOLDOWN_SECONDS

    async def set_cooldown_seconds(self, game_id: int, seconds: int) -> None:
        await self._conn.execute(
            "UPDATE games SET cooldown_seconds = ?, updated_at = datetime('now') WHERE id = ?",
            (seconds, game_id),
        )
        await self._conn.commit()

    # -- channel freeze (persisted, survives restarts) -------------------------
    async def is_frozen(self) -> bool:
        cursor = await self._conn.execute(
            "SELECT value FROM bot_settings WHERE key = ?", (_FROZEN_KEY,)
        )
        row = await cursor.fetchone()
        return row is not None and row["value"] == "1"

    async def set_frozen(self, frozen: bool) -> None:
        await self._conn.execute(
            """
            INSERT INTO bot_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (_FROZEN_KEY, "1" if frozen else "0"),
        )
        await self._conn.commit()

    # -- deletion --------------------------------------------------------------
    async def delete_game(self, game_id: int, delete_messages: bool) -> None:
        """
        Delete a game and its memberships.

        game_players rows hold the chat-to-game linking (private_chat_id), so
        removing them also unlinks every chat from this game. Message history
        is only removed when delete_messages is True (messages has no foreign
        key to games, so keeping them is safe).
        """
        try:
            await self._conn.execute("DELETE FROM game_players WHERE game_id = ?", (game_id,))
            if delete_messages:
                await self._conn.execute("DELETE FROM messages WHERE game_id = ?", (game_id,))
            await self._conn.execute("DELETE FROM games WHERE id = ?", (game_id,))
            await self._conn.commit()
        except Exception:
            await self._conn.rollback()
            raise
