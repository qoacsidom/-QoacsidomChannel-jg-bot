"""Global error handler: logs exceptions without ever leaking secrets."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception while processing an update: %s", update, exc_info=context.error)

    if isinstance(update, Update) and update.effective_message is not None:
        try:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong processing that. It has been logged for the admin."
            )
        except Exception:
            logger.exception("Failed to notify the user about a prior error.")
