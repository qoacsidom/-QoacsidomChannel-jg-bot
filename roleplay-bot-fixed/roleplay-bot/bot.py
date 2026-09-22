"""
Entry point for the Roleplay Bot.

Run with:  python bot.py
(from inside this project's root folder, with a .env file present)
"""
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import ConfigError, load_config
from database import init_database
from handlers.admin import admin_callback, admin_command, build_create_game_conversation
from handlers.dispatch import handle_group_message
from handlers.errors import error_handler
from handlers.start import start_command
from repositories.games import GameRepository
from repositories.messages import MessageRepository
from repositories.players import PlayerRepository

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _post_init(application: Application) -> None:
    config = application.bot_data["config"]
    connection = await init_database(config.database_path)
    application.bot_data["db"] = connection
    application.bot_data["game_repo"] = GameRepository(connection)
    application.bot_data["player_repo"] = PlayerRepository(connection)
    application.bot_data["message_repo"] = MessageRepository(connection)
    logger.info("Bot initialized and ready to poll for updates.")


async def _post_shutdown(application: Application) -> None:
    connection = application.bot_data.get("db")
    if connection is not None:
        await connection.close()
        logger.info("Database connection closed.")
        
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

def main() -> None:
    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        raise SystemExit(1) from exc

    application = (
        Application.builder()
        .token(config.bot_token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    application.bot_data["config"] = config

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(build_create_game_conversation())
    application.add_handler(
        CallbackQueryHandler(admin_callback, pattern=r"^admin:(list_games|list_players|help|link:\d+)$")
    )

    # Single catch-all for everything else in group/supergroup chats
    # (ordinary player content + admin reply-commands are both decided
    # inside handle_group_message). Excludes commands (handled above) and
    # service messages (member joined/left, pinned, etc.).
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & filters.UpdateType.MESSAGE  # ignore edited messages (would re-publish)
            & ~filters.COMMAND
            & ~filters.StatusUpdate.ALL,
            handle_group_message,
        )
    )

    application.add_error_handler(error_handler)

    logger.info("Starting polling…")
    threading.Thread(target=run_health_server, daemon=True).start()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
