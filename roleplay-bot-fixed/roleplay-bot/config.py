"""
Configuration loader for the Roleplay Bot.

All configuration comes from environment variables (loaded from a local
.env file in development, or real environment variables in production).
The bot token and other secrets are NEVER hardcoded here.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_user_id: int
    channel_id: str
    database_path: str


def load_config() -> Config:
    """
    Load configuration from environment variables.

    Raises:
        ConfigError: if a required variable is missing or malformed.
    """
    load_dotenv()  # loads variables from a local .env file, if present

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ConfigError(
            "BOT_TOKEN is not set. Copy .env.example to .env and set BOT_TOKEN "
            "to the token you received from @BotFather."
        )

    admin_raw = os.getenv("ADMIN_USER_ID", "").strip()
    if not admin_raw:
        raise ConfigError("ADMIN_USER_ID is not set in the environment.")
    try:
        admin_user_id = int(admin_raw)
    except ValueError as exc:
        raise ConfigError(
            f"ADMIN_USER_ID must be a numeric Telegram user ID, got: {admin_raw!r}"
        ) from exc

    channel_id = os.getenv("CHANNEL_ID", "").strip()
    if not channel_id:
        raise ConfigError("CHANNEL_ID is not set in the environment.")

    database_path = os.getenv("DATABASE_PATH", "data/roleplay_bot.db").strip()

    # NOTE: bot_token is intentionally never logged, here or anywhere else.
    logger.info(
        "Configuration loaded (admin_user_id=%s, channel_id=%s, database_path=%s).",
        admin_user_id,
        channel_id,
        database_path,
    )

    return Config(
        bot_token=bot_token,
        admin_user_id=admin_user_id,
        channel_id=channel_id,
        database_path=database_path,
    )
