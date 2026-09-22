# Roleplay Bot

A lightweight Telegram bot for running 2-3 concurrent multiplayer roleplay
games. Players send plain text/photos in a private group; the bot posts
them to a public channel formatted with their Roleplay identity. The admin
manages each player's identity by replying to their messages with short
Persian commands.

## 1. Requirements

- Python 3.11 or newer
- A Telegram account
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## 2. Project structure

```
roleplay-bot/
├── bot.py                    # Entry point
├── config.py                 # Loads/validates .env
├── constants.py               # Persian commands + all bot-facing text
├── database.py                 # Schema creation (auto-runs on startup)
├── repositories/
│   ├── games.py                # games table
│   ├── players.py               # players + game_players + chat linking
│   └── messages.py               # immutable message history
├── services/
│   ├── identity.py                # Persian command parser (pure logic)
│   ├── tracking.py                 # tracks senders before a chat is linked
│   └── forwarding.py                # builds + sends the channel post
├── handlers/
│   ├── start.py                      # /start (never auto-authorizes)
│   ├── player.py                      # forwards player content
│   ├── admin.py                        # reply-commands + /admin menu
│   ├── dispatch.py                      # routes group messages
│   └── errors.py                         # global error handler
├── tests/test_identity.py                 # unit tests (no Telegram needed)
├── requirements.txt
├── .env.example
├── .gitignore
└── data/                                    # SQLite file lives here
```

This deviates slightly from a flat `handlers/commands.py` file: identity
management (`admin.py`) and message relaying (`player.py`) are split out,
and a small `repositories/` and `services/` layer separates database
access, business logic, and Telegram wiring. It's still a small, flat
project - nothing here needs a framework beyond python-telegram-bot itself.

## 3. Create the bot with BotFather

1. Open a chat with [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Follow the prompts to name it; BotFather gives you a token like
   `123456789:AAExampleTokenDoNotUseThisOne`.
3. **Disable privacy mode** - this is critical, see the warning box below:
   - Send `/setprivacy` to BotFather
   - Choose your bot
   - Choose **Disable**

> ⚠️ **Why this matters:** by default, Telegram bots in group chats only
> receive messages that start with `/`, that @mention the bot, or that
> reply to the bot's own messages. With privacy mode ON, the bot would
> never see a player's plain text ("We entered the city.") or the admin's
> replies to the *player's* messages - which is exactly how this bot's
> core workflow works. If commands or player messages seem to do nothing,
> this is almost always the cause.

## 4. Configure

```bash
cp .env.example .env
```

Edit `.env` and set `BOT_TOKEN` to the token from BotFather. The example
file already includes the admin ID and channel from your spec
(`ADMIN_USER_ID=6427916800`, `CHANNEL_ID=@JewishGamesNews`) - change them
if needed. Never commit `.env` or paste your real token anywhere (chat,
README, git).

## 5. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 6. Database

Nothing to do - `bot.py` creates `data/roleplay_bot.db` and all tables
automatically on first run.

## 7. Run the bot

```bash
python bot.py
```

Run this from inside the `roleplay-bot/` folder (so the `data/` path and
Python imports resolve correctly). Stop with `Ctrl+C`.

## 8. Add the bot to the main channel

1. Open your channel (`@JewishGamesNews` or whatever you configured).
2. Add the bot as an **administrator**.
3. Grant it **"Post Messages"** permission (that's the only one it needs).

Without this, every forward attempt will fail and the player will see
"Failed to post to the channel."

## 9. Required Telegram permissions - summary

| Context | What the bot needs |
|---|---|
| Player's private group | Member; **privacy mode disabled** (step 3) |
| Main channel | Administrator with "Post Messages" |
| Admin's DM with the bot | Nothing special - just start a chat with it |

A private group with only 3 members (you, the player, the bot) does not
need to be a supergroup - a plain Telegram "group" works fine and has no
practical limit that matters at this scale.

## 10. Creating a game and adding a player - step by step

1. **Create the game.** DM the bot, send `/admin`, tap **➕ Create Game**,
   then type a name (e.g. `World War II`).
2. **Create the private group.** In Telegram, create a new group, add the
   player and the bot to it. (Add the bot *before* the player starts
   sending roleplay messages - a bot cannot see messages sent before it
   joined a chat.)
3. **Get the player's Telegram ID.** Ask the player to send any message
   in that group (e.g. "hi"). Telegram gives bots no way to look up a
   user's numeric ID from just their @username, so this step is
   unavoidable - it's the only way the bot learns who they are.
4. **Link the chat to the game.** In that same group, send `/admin`, tap
   **🔗 Link this chat to a game**, and pick the game from the list.
5. **Set their identity.** Reply to the player's earlier message with:
   ```
   تنظیم اسم فرمانده علی
   ```
   and
   ```
   تنظیم کشور ایران
   ```
6. Done - the player can now send text or photos and they'll appear in
   the channel with their Roleplay identity attached.

## 11. Admin commands reference

All five are sent **as a reply to one of the player's messages**, inside
that player's private group:

| Command | Effect |
|---|---|
| `تنظیم کشور <value>` | Sets Country/Faction, e.g. `تنظیم کشور باد`, `تنظیم کشور Kingdom of Nothing` |
| `تنظیم اسم <value>` | Sets Display Name, e.g. `تنظیم اسم پادشاه باد` |
| `فعال` | Activates the player in this game |
| `غیرفعال` | Deactivates the player (their messages stop being published) |
| `اطلاعات` | Shows the player's current game/name/country/username/ID/status |

The value after `تنظیم کشور` / `تنظیم اسم` is never validated against any
list - it's a free-form display string, exactly as specified.

`/admin` in your **DM** with the bot also gives you **📋 List Games** and
**👥 List Players**, and toggling a game's active state can be added the
same way if you need it later (deactivating a whole game is currently
done at the database/repository level - ask if you want a menu button for it).

## 12. Security model

- **Numeric ID only.** Every admin check compares
  `update.effective_user.id` against `ADMIN_USER_ID`. Usernames and
  Roleplay names are never used for authentication or authorization.
- **Reply target must be the tracked player.** An admin command is only
  applied if it is a reply, the chat is linked to a game, *and* the
  replied-to message's sender ID matches that game membership's
  `telegram_user_id`. Replying to your own message, to the bot's message,
  or in an unlinked chat is rejected with a clear error - a command can
  never be "aimed" at the wrong player by guessing.
- **Players can't touch identity.** Only the reply-command handler (admin
  ID gated) can write to `display_name` / `country_or_faction` / `active`.
  Nothing in the player-message path can modify these fields.
- **Parameterized SQL everywhere.** No query ever concatenates user input
  into SQL text.
- **Token hygiene.** The token is read from the environment, is never
  logged, and never appears in any committed file.

## 13. How historical data integrity works

Every time a message is forwarded, `messages.display_name_at_message`,
`country_or_faction_at_message`, and `telegram_username_at_message` are
filled in from the player's *current* state at that exact moment, then
never touched again. The only field ever updated on an existing `messages`
row afterward is `channel_message_id` (attached right after the post
succeeds). Country/name changes only ever update the `game_players` table
(the "current" state) - so:

- Old channel posts keep showing the identity the player had *at the time*.
- New posts pick up whatever the admin most recently set.

## 14. Telegram API behavior and limitations (read this before deploying)

- **Privacy mode** must be disabled (step 3) or the bot won't see plain
  player messages or admin replies-to-players at all - it's the single
  most common setup mistake.
- **No username → ID lookup.** A bot cannot resolve `@username` to a
  numeric ID unless it has already seen a message from that user. This is
  why linking a chat requires the player to send at least one message first.
- **Bots don't see history before they joined.** Add the bot to a private
  group *before* the player starts talking there.
- **`copy_message` vs. `forward_message`.** The bot uses `copy_message`,
  which re-sends the content without a "Forwarded from" tag and lets us
  fully replace the caption/text with the identity header. Telegram
  handles the photo file server-side - there's no download/re-upload.
- **Caption length limit.** Photo captions are capped at 1024 characters
  (plain text messages allow 4096). If the header + caption would exceed
  that, the bot posts the photo with just the header and sends the full
  original caption as a separate follow-up message, rather than
  truncating it.
- **@mentions auto-link on their own.** The channel header is sent as
  plain text (no Markdown/HTML parse mode) specifically because Roleplay
  names/countries are arbitrary admin-entered strings that could otherwise
  break Markdown parsing. Telegram clients still auto-link a plain
  `@username` in the text - no special formatting is needed for that.
- **A bot can't read channel messages it posts** as a normal update - if
  you ever want the bot to react to comments on channel posts, that needs
  a *discussion group* linked to the channel, which is out of scope here.

## 15. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Bot never reacts to plain player text | Privacy mode is still enabled - see step 3 |
| Admin reply-command says "not associated with a tracked player" | You replied to the bot's or your own message instead of the player's, or the chat isn't linked yet |
| Admin command says "must be sent as a reply" | You sent it without replying to anything |
| "This chat has not been configured" | Nobody has linked this chat to a game yet (`/admin` → Link this chat) |
| "No message from a player has been seen in this chat yet" | Ask the player to send one message, then retry linking |
| "Failed to post to the channel" | The bot isn't an admin in the channel, or lacks "Post Messages" |
| Bot won't start / `ConfigError` | Check `.env` exists and `BOT_TOKEN` / `ADMIN_USER_ID` / `CHANNEL_ID` are all set |

## 16. Free/low-resource hosting notes

- The bot uses long polling, so it needs a host that keeps a process
  running continuously - not a serverless/on-demand function.
- **Persistent disk matters.** Many free hosting tiers wipe the local
  filesystem on redeploy or sleep/wake cycles, which would silently erase
  `data/roleplay_bot.db`. Confirm your host offers a persistent volume/disk
  for the `data/` folder, or point `DATABASE_PATH` at a mounted volume.
- A small always-on VPS, or a host with an explicit persistent-disk add-on,
  is more predictable for this than a pure "free web service" tier.

## 17. Manual test checklist

**Player**
- [ ] Authorized active player sends text → appears in channel with correct header
- [ ] Authorized active player sends photo → appears in channel, no re-upload artifacts
- [ ] Authorized active player sends photo + caption → both appear together
- [ ] Unauthorized user (unlinked chat) sends a message → gets "not configured" notice, nothing posted
- [ ] Disabled (`غیرفعال`) player sends a message → gets "inactive" notice, nothing posted

**Admin**
- [ ] `تنظیم کشور ایران` and `تنظیم کشور باد` both work, arbitrary strings accepted
- [ ] `تنظیم اسم علی` and `تنظیم اسم پادشاه باد` both work
- [ ] `فعال` re-activates a disabled player
- [ ] `غیرفعال` deactivates a player
- [ ] `اطلاعات` shows game/name/country/username/ID/status correctly

**Security**
- [ ] Non-admin sending a reply with a command prefix → treated as normal chat, nothing changes
- [ ] Admin sends a command with no reply → "must be sent as a reply"
- [ ] Admin replies to an unrelated message (their own, or the bot's) → "not associated with a tracked player"
- [ ] Two players have identical Display Names → both work independently, no conflict
- [ ] Player changes their Telegram username → old channel posts keep the old @username; new posts show the new one
- [ ] Same Telegram user linked into two different games (two different private groups) → each has its own independent name/country

**Historical data**
- [ ] Change a player's country/name, then compare an old channel post vs. a new one → old post is unchanged, new post reflects the update

## Running the automated unit tests (optional)

```bash
python3 -m unittest discover -s tests
```

These only cover the Persian command parser (pure string logic - no
Telegram connection needed). Everything else in this checklist has to be
tested against a live bot, since it depends on real Telegram API behavior.
