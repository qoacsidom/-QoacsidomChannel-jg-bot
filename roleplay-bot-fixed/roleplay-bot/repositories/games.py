"""Data access for the `games` table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import aiosqlite


@dataclass
class Game:
    id: int
    name: str
    active: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Game":
        return cls(
            id=row["id"],
            name=row["name"],
            active=bool(row["active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
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
