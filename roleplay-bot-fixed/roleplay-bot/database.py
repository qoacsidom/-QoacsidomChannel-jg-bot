"""
Database setup for the Roleplay Bot.

Uses aiosqlite so all database access is non-blocking and plays nicely
with python-telegram-bot's asyncio event loop. The schema is created
automatically on startup (CREATE TABLE IF NOT EXISTS) - there is no
separate migration step for v1.
"""

from __future__ import annotations

import logging
import os

import aiosqlite

logger = logging.getLogger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_user_id INTEGER NOT NULL UNIQUE,
    telegram_username TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One row = one player's membership in one game. private_chat_id is the
-- dedicated Telegram group for THIS specific player+game combination (a
-- player who is in two games has two separate private chats/rows).
CREATE TABLE IF NOT EXISTS game_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL REFERENCES games(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    display_name TEXT NOT NULL DEFAULT '',
    country_or_faction TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    private_chat_id INTEGER UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(game_id, player_id)
);

-- Immutable historical log. display_name_at_message / country_or_faction_at_message
-- / telegram_username_at_message are a frozen snapshot taken at send time and
-- must NEVER be edited after insert - only channel_message_id is ever attached
-- afterward (see MessageRepository.attach_channel_message_id).
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    telegram_user_id INTEGER NOT NULL,
    display_name_at_message TEXT NOT NULL,
    country_or_faction_at_message TEXT NOT NULL,
    telegram_username_at_message TEXT,
    telegram_message_id INTEGER NOT NULL,
    private_chat_id INTEGER NOT NULL,
    channel_message_id INTEGER,
    message_type TEXT NOT NULL,
    text_or_caption TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Temporary holding area: the most recent non-admin sender seen in a group
-- chat that isn't linked to a game yet. Telegram gives bots no way to look
-- up a user's numeric ID from just their @username, so we need to have
-- observed at least one message from them before the admin can link the chat.
CREATE TABLE IF NOT EXISTS pending_chat_senders (
    private_chat_id INTEGER PRIMARY KEY,
    telegram_user_id INTEGER NOT NULL,
    telegram_username TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_game ON messages(game_id);
CREATE INDEX IF NOT EXISTS idx_messages_player ON messages(player_id);
CREATE INDEX IF NOT EXISTS idx_game_players_chat ON game_players(private_chat_id);
"""


async def init_database(database_path: str) -> aiosqlite.Connection:
    """
    Open (creating if necessary) the SQLite database and ensure the schema
    exists. Returns a long-lived connection meant to be reused for the
    bot's entire lifetime (stored in application.bot_data).
    """
    directory = os.path.dirname(database_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    connection = await aiosqlite.connect(database_path)
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys = ON;")
    await connection.execute("PRAGMA journal_mode = WAL;")
    await connection.executescript(SCHEMA)
    await connection.commit()

    logger.info("Database ready at %s", database_path)
    return connection
