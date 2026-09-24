"""
Admin functionality:

1. Reply-based Persian commands, sent inside a player's private group as a
   reply to one of the player's own messages:
   تنظیم کشور <value> / تنظیم اسم <value> / فعال / غیرفعال / اطلاعات

2. The /admin menu:
   - in a private chat with the bot: create games, list games/players
   - inside a player's private group: link that chat to a game

Every action here re-checks the numeric admin Telegram user ID; nothing
here ever trusts a username or a Roleplay display name for authentication.
"""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from constants import (
    ALLOWED_COOLDOWNS,
    BTN_CANCEL,
    BTN_DELETE_EVERYTHING,
    BTN_KEEP_MESSAGES,
    CMD_SET_COUNTRY,
    CMD_SET_NAME,
    INFO_TEMPLATE,
    MSG_ADMIN_NO_REPLY,
    MSG_ADMIN_REPLY_UNTRACKED,
    MSG_CHANNEL_UNFROZEN,
    MSG_COUNTRY_UPDATED,
    MSG_DELETE_CANCELLED,
    MSG_DELETE_CONFIRM,
    MSG_DELETE_MESSAGES_DELETED,
    MSG_DELETE_MESSAGES_KEPT,
    MSG_DELETE_PICK_GAME,
    MSG_FREEZE_OK,
    MSG_GAME_DELETED,
    MSG_GAME_NOT_FOUND,
    MSG_LINK_ALREADY_LINKED,
    MSG_LINK_ALREADY_MEMBER,
    MSG_LINK_NO_PENDING_SENDER,
    MSG_LINK_SUCCESS,
    MSG_NAME_UPDATED,
    MSG_NO_GAMES,
    MSG_NOT_ADMIN,
    MSG_PLAYER_ACTIVATED,
    MSG_PLAYER_DEACTIVATED,
    MSG_SETCOOLDOWN_NEED_GAME,
    MSG_SETCOOLDOWN_OK,
    MSG_SETCOOLDOWN_USAGE,
    NO_USERNAME_TEXT,
)
from services.identity import parse_admin_command

logger = logging.getLogger(__name__)

AWAITING_GAME_NAME = 1


def _is_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    return user_id == context.bot_data["config"].admin_user_id


# ---------------------------------------------------------------------
# 1. Reply-based commands (typed inside a player's private group)
# ---------------------------------------------------------------------

async def handle_admin_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Precondition (guaranteed by handlers/dispatch.py): update.effective_user.id
    is the configured admin, and message.reply_to_message is not None.
    """
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None or not message.text:
        return

    parsed = parse_admin_command(message.text)
    if parsed is None:
        return  # admin just chatting in the group; not a recognized command

    if message.reply_to_message is None:
        await message.reply_text(MSG_ADMIN_NO_REPLY)
        return

    player_repo = context.bot_data["player_repo"]
    link = await player_repo.get_by_chat(chat.id)
    replied_user = message.reply_to_message.from_user

    if link is None or replied_user is None or replied_user.id != link.telegram_user_id:
        await message.reply_text(MSG_ADMIN_REPLY_UNTRACKED)
        return

    if parsed.action == "set_country":
        await player_repo.update_country(link.id, parsed.value)
        await message.reply_text(MSG_COUNTRY_UPDATED.format(value=parsed.value))

    elif parsed.action == "set_name":
        await player_repo.update_display_name(link.id, parsed.value)
        await message.reply_text(MSG_NAME_UPDATED.format(value=parsed.value))

    elif parsed.action == "activate":
        await player_repo.set_active(link.id, True)
        await message.reply_text(MSG_PLAYER_ACTIVATED)

    elif parsed.action == "deactivate":
        await player_repo.set_active(link.id, False)
        await message.reply_text(MSG_PLAYER_DEACTIVATED)

    elif parsed.action == "info":
        username = replied_user.username
        info_text = INFO_TEMPLATE.format(
            game_name=link.game_name,
            display_name=link.display_name or "(not set)",
            country=link.country_or_faction or "(not set)",
            username_display=f"@{username}" if username else NO_USERNAME_TEXT,
            telegram_user_id=link.telegram_user_id,
            status="Active" if link.active else "Inactive",
        )
        await message.reply_text(info_text)

    logger.info(
        "Admin command '%s' applied to game_player_id=%s in chat_id=%s",
        parsed.action, link.id, chat.id,
    )


# ---------------------------------------------------------------------
# 2. /admin menu
# ---------------------------------------------------------------------

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    if user is None or chat is None or message is None:
        return

    if not _is_admin(context, user.id):
        await message.reply_text(MSG_NOT_ADMIN)
        return

    if chat.type in ("group", "supergroup"):
        await _send_group_admin_menu(update, context, chat.id)
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create Game", callback_data="admin:create_game")],
            [InlineKeyboardButton("📋 List Games", callback_data="admin:list_games")],
            [InlineKeyboardButton("👥 List Players", callback_data="admin:list_players")],
            [InlineKeyboardButton("🗑️ Delete Game", callback_data="admin:delete_game")],
            [InlineKeyboardButton("❓ Help", callback_data="admin:help")],
        ])
        await message.reply_text("🛠 Admin menu:", reply_markup=keyboard)


async def _send_group_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    message = update.effective_message
    player_repo = context.bot_data["player_repo"]
    link = await player_repo.get_by_chat(chat_id)

    if link is not None:
        text = (
            "ℹ️ This chat is linked to:\n"
            f"Game: {link.game_name}\n"
            f"Display Name: {link.display_name or '(not set)'}\n"
            f"Country/Faction: {link.country_or_faction or '(not set)'}\n"
            f"Status: {'Active' if link.active else 'Inactive'}"
        )
        await message.reply_text(text)
        return

    game_repo = context.bot_data["game_repo"]
    games = await game_repo.list_active()
    if not games:
        await message.reply_text(
            "⚠️ No active games exist yet. Create one first with /admin in a private chat with me."
        )
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(g.name, callback_data=f"admin:link:{g.id}")] for g in games]
    )
    await message.reply_text("🔗 Link this chat to a game:", reply_markup=keyboard)


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the stateless admin menu buttons (everything except 'Create Game')."""
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return

    if not _is_admin(context, user.id):
        await query.answer("Not authorized.", show_alert=True)
        return

    await query.answer()
    data = query.data or ""

    if data == "admin:list_games":
        game_repo = context.bot_data["game_repo"]
        games = await game_repo.list_all()
        if not games:
            await query.edit_message_text("No games yet.")
            return
        lines = [f"{'🟢' if g.active else '🔴'} [{g.id}] {g.name}" for g in games]
        await query.edit_message_text("📋 Games:\n" + "\n".join(lines))

    elif data == "admin:list_players":
        player_repo = context.bot_data["player_repo"]
        players = await player_repo.list_all()
        if not players:
            await query.edit_message_text("No players yet.")
            return
        lines = [
            f"{'🟢' if p.active else '🔴'} {p.display_name or '(unnamed)'} "
            f"— {p.game_name} — id {p.telegram_user_id}"
            for p in players
        ]
        await query.edit_message_text("👥 Players:\n" + "\n".join(lines))

    elif data == "admin:help":
        await query.edit_message_text(
            "Reply to a player's message in their private group with one of:\n\n"
            f"{CMD_SET_COUNTRY} <value>\n"
            f"{CMD_SET_NAME} <value>\n"
            "فعال   (activate)\n"
            "غیرفعال   (deactivate)\n"
            "اطلاعات   (info)\n\n"
            "Slash commands (admin only):\n"
            "/setcooldown <30|60|120> [game_id]\n"
            "/freeze\n"
            "/unfreeze"
        )

    elif data == "admin:delete_game":
        game_repo = context.bot_data["game_repo"]
        games = await game_repo.list_all()
        if not games:
            await query.edit_message_text(MSG_NO_GAMES)
            return
        rows = [
            [InlineKeyboardButton(f"[{g.id}] {g.name}", callback_data=f"admin:delgame:{g.id}")]
            for g in games
        ]
        rows.append([InlineKeyboardButton(BTN_CANCEL, callback_data="admin:delcancel")])
        await query.edit_message_text(MSG_DELETE_PICK_GAME, reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("admin:delgame:"):
        game_id = int(data.split(":", 2)[2])
        game = await context.bot_data["game_repo"].get_by_id(game_id)
        if game is None:
            await query.edit_message_text(MSG_GAME_NOT_FOUND)
            return
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(BTN_DELETE_EVERYTHING, callback_data=f"admin:delconfirm:{game_id}:all")],
            [InlineKeyboardButton(BTN_KEEP_MESSAGES, callback_data=f"admin:delconfirm:{game_id}:keep")],
            [InlineKeyboardButton(BTN_CANCEL, callback_data="admin:delcancel")],
        ])
        await query.edit_message_text(MSG_DELETE_CONFIRM.format(name=game.name), reply_markup=keyboard)

    elif data.startswith("admin:delconfirm:"):
        _, _, raw_game_id, mode = data.split(":", 3)
        game_id = int(raw_game_id)
        # Default is "Keep messages": only an explicit "all" removes history.
        delete_messages = mode == "all"
        game_repo = context.bot_data["game_repo"]
        game = await game_repo.get_by_id(game_id)
        if game is None:
            await query.edit_message_text(MSG_GAME_NOT_FOUND)
            return
        await game_repo.delete_game(game_id, delete_messages=delete_messages)
        logger.info("Admin deleted game_id=%s (delete_messages=%s)", game_id, delete_messages)
        await query.edit_message_text(
            MSG_GAME_DELETED.format(
                name=game.name,
                messages=MSG_DELETE_MESSAGES_DELETED if delete_messages else MSG_DELETE_MESSAGES_KEPT,
            )
        )

    elif data == "admin:delcancel":
        await query.edit_message_text(MSG_DELETE_CANCELLED)

    elif data.startswith("admin:link:"):
        game_id = int(data.split(":", 2)[2])
        await _link_chat_to_game(query, context, game_id)


async def _link_chat_to_game(query, context: ContextTypes.DEFAULT_TYPE, game_id: int) -> None:
    chat_id = query.message.chat.id
    player_repo = context.bot_data["player_repo"]
    game_repo = context.bot_data["game_repo"]

    if await player_repo.get_by_chat(chat_id) is not None:
        await query.edit_message_text(MSG_LINK_ALREADY_LINKED)
        return

    pending = await player_repo.get_pending_sender(chat_id)
    if pending is None:
        await query.edit_message_text(MSG_LINK_NO_PENDING_SENDER)
        return

    game = await game_repo.get_by_id(game_id)
    if game is None:
        await query.edit_message_text("⚠️ That game no longer exists.")
        return

    existing_membership = await player_repo.find_membership(game_id, pending["telegram_user_id"])
    if existing_membership is not None:
        await query.edit_message_text(
            MSG_LINK_ALREADY_MEMBER.format(display_name=existing_membership.display_name or "(not set)")
        )
        return

    link = await player_repo.link_chat_to_game(
        private_chat_id=chat_id,
        game_id=game_id,
        telegram_user_id=pending["telegram_user_id"],
        username=pending["telegram_username"],
    )
    await player_repo.clear_pending_sender(chat_id)

    await query.edit_message_text(
        MSG_LINK_SUCCESS.format(
            game_name=game.name,
            telegram_user_id=link.telegram_user_id,
            set_name=CMD_SET_NAME,
            set_country=CMD_SET_COUNTRY,
        )
    )


# ---------------------------------------------------------------------
# 2b. /setcooldown, /freeze, /unfreeze (admin-only slash commands)
# ---------------------------------------------------------------------

async def setcooldown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/setcooldown <30|60|120> [game_id] - sets the per-game anti-spam cooldown."""
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    if user is None or chat is None or message is None:
        return

    if not _is_admin(context, user.id):
        await message.reply_text(MSG_NOT_ADMIN)
        return

    args = context.args or []
    if (
        not args
        or len(args) > 2
        or not (args[0].isascii() and args[0].isdigit())
        or int(args[0]) not in ALLOWED_COOLDOWNS
        or (len(args) == 2 and not (args[1].isascii() and args[1].isdigit()))
    ):
        await message.reply_text(MSG_SETCOOLDOWN_USAGE)
        return

    seconds = int(args[0])
    game_repo = context.bot_data["game_repo"]
    player_repo = context.bot_data["player_repo"]
    game = None

    if len(args) == 2:
        game = await game_repo.get_by_id(int(args[1]))
        if game is None:
            await message.reply_text(MSG_GAME_NOT_FOUND)
            return
    else:
        link = None
        if chat.type in ("group", "supergroup"):
            link = await player_repo.get_by_chat(chat.id)
        if link is not None:
            game = await game_repo.get_by_id(link.game_id)
        else:
            games = await game_repo.list_all()
            if not games:
                await message.reply_text(MSG_NO_GAMES)
                return
            if len(games) == 1:
                game = games[0]
            else:
                lines = [f"[{g.id}] {g.name} ({g.cooldown_seconds}s)" for g in games]
                await message.reply_text(MSG_SETCOOLDOWN_NEED_GAME.format(games="\n".join(lines)))
                return

    if game is None:
        await message.reply_text(MSG_GAME_NOT_FOUND)
        return

    await game_repo.set_cooldown_seconds(game.id, seconds)
    logger.info("Admin set cooldown for game_id=%s to %ss", game.id, seconds)
    await message.reply_text(MSG_SETCOOLDOWN_OK.format(name=game.name, seconds=seconds))


async def freeze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    if not _is_admin(context, user.id):
        await message.reply_text(MSG_NOT_ADMIN)
        return

    await context.bot_data["game_repo"].set_frozen(True)
    logger.info("Admin froze the channel.")
    await message.reply_text(MSG_FREEZE_OK)


async def unfreeze_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return

    if not _is_admin(context, user.id):
        await message.reply_text(MSG_NOT_ADMIN)
        return

    await context.bot_data["game_repo"].set_frozen(False)
    logger.info("Admin unfroze the channel.")
    await message.reply_text(MSG_CHANNEL_UNFROZEN)


# ---------------------------------------------------------------------
# 3. "Create Game" conversation (the only admin flow that needs free-text input)
# ---------------------------------------------------------------------

async def create_game_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or not _is_admin(context, user.id):
        if query is not None:
            await query.answer("Not authorized.", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    await query.edit_message_text("✏️ Send the name of the new game as a plain text message. Send /cancel to abort.")
    return AWAITING_GAME_NAME


async def create_game_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    name = (message.text or "").strip()
    if not name:
        await message.reply_text("⚠️ Game name cannot be empty. Try again, or /cancel.")
        return AWAITING_GAME_NAME

    game_repo = context.bot_data["game_repo"]
    game = await game_repo.create(name)
    await message.reply_text(f"✅ Game created: [{game.id}] {game.name}")
    return ConversationHandler.END


async def create_game_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("Cancelled.")
    return ConversationHandler.END


def build_create_game_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(create_game_start, pattern="^admin:create_game$")],
        states={
            AWAITING_GAME_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_game_receive_name)],
        },
        fallbacks=[CommandHandler("cancel", create_game_cancel)],
        conversation_timeout=300,
    )
