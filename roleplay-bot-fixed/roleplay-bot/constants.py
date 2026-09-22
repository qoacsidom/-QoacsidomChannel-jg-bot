"""
Constants: Persian admin command prefixes and bot-facing text templates.

Keeping every user-facing string here means the bot's language/wording can
be changed (e.g. translated to Persian) without touching any handler logic.
"""

# --- Persian admin command prefixes -------------------------------------
# These must match exactly what the admin types when replying to a
# player's message. Do not change these without updating README.md.
CMD_SET_COUNTRY = "تنظیم کشور"
CMD_SET_NAME = "تنظیم اسم"
CMD_ACTIVATE = "فعال"
CMD_DEACTIVATE = "غیرفعال"
CMD_INFO = "اطلاعات"

# --- Channel post formatting ---------------------------------------------
CHANNEL_TEMPLATE = (
    "🎮 {game_name}\n"
    "\n"
    "🏳️ {country}\n"
    "👤 {display_name}\n"
    "🔗 {username_display}\n"
    "🆔 {telegram_user_id}\n"
    "\n"
    "{content}"
)

NO_USERNAME_TEXT = "No username"

# Telegram hard limits (Bot API)
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024

# --- Admin "اطلاعات" (info) output ---------------------------------------
INFO_TEMPLATE = (
    "Game: {game_name}\n"
    "Display Name: {display_name}\n"
    "Country/Faction: {country}\n"
    "Telegram Username: {username_display}\n"
    "Telegram User ID: {telegram_user_id}\n"
    "Status: {status}"
)

# --- Player-facing messages ------------------------------------------------
MSG_START_GENERIC = (
    "👋 Hello! This bot relays roleplay messages for private games.\n\n"
    "You are not automatically registered. An admin needs to set up your "
    "game membership before your messages will be published."
)

MSG_CHAT_NOT_LINKED = (
    "🕓 This chat has not been configured by the admin yet. Please wait for setup to finish."
)

MSG_PLAYER_INACTIVE = "⚠️ You are currently inactive in this game. Your message was not published."

MSG_GAME_INACTIVE = "⚠️ This game is currently inactive. Your message was not published."

MSG_UNSUPPORTED_MEDIA = "⚠️ Only text messages and photos (with optional captions) are supported."

MSG_UNKNOWN_SENDER_IN_LINKED_CHAT = (
    "⚠️ This message was not published because it did not come from the registered "
    "player for this chat."
)

MSG_CHANNEL_SEND_FAILED = (
    "⚠️ Failed to post to the channel. Please ask the admin to confirm the bot is an "
    "administrator there with permission to post messages."
)

# --- Admin-facing messages ------------------------------------------------
MSG_NOT_ADMIN = "⛔ This command is restricted to the bot administrator."

MSG_ADMIN_NO_REPLY = "⚠️ This command must be sent as a reply to the player's message."

MSG_ADMIN_REPLY_UNTRACKED = (
    "⚠️ The message you replied to is not associated with a tracked player in this "
    "chat. No changes were made."
)

MSG_COUNTRY_UPDATED = "✅ Country/faction updated to: {value}"
MSG_NAME_UPDATED = "✅ Display name updated to: {value}"
MSG_PLAYER_ACTIVATED = "✅ Player activated. They can now post to the channel."
MSG_PLAYER_DEACTIVATED = "✅ Player deactivated. They can no longer post to the channel."

MSG_LINK_NO_PENDING_SENDER = (
    "⚠️ No message from a player has been seen in this chat yet. Ask the player to "
    "send any message here, then try linking again."
)

MSG_LINK_ALREADY_LINKED = "ℹ️ This chat is already linked to a game."

MSG_LINK_ALREADY_MEMBER = (
    "⚠️ This Telegram user is already a member of that game in a different chat.\n"
    "Existing display name: {display_name}"
)

MSG_LINK_SUCCESS = (
    "✅ This chat is now linked!\n"
    "Game: {game_name}\n"
    "Player Telegram ID: {telegram_user_id}\n\n"
    "Next: reply to the player's message with '{set_name} <value>' or "
    "'{set_country} <value>' to set their identity."
)
