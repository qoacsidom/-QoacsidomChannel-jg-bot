"""
Regression tests for the SQL layer (needs `aiosqlite`, which is in requirements.txt).

Guards against the bug where GamePlayerRecord.from_row read
row["telegram_user_id"] but the SELECT never returned that column, which made
get_by_chat / get_by_id / find_membership / list_* raise IndexError.

Run with:  python3 -m unittest discover -s tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import aiosqlite  # noqa: F401
except ImportError:  # pragma: no cover
    aiosqlite = None

if aiosqlite is not None:
    from database import init_database
    from repositories.games import GameRepository
    from repositories.players import PlayerRepository


@unittest.skipIf(aiosqlite is None, "aiosqlite is not installed")
class TestPlayerRepository(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.conn = await init_database(str(Path(self._tmp.name) / "test.db"))
        self.games = GameRepository(self.conn)
        self.players = PlayerRepository(self.conn)
        self.game = await self.games.create("WW2")

    async def asyncTearDown(self):
        await self.conn.close()
        self._tmp.cleanup()

    async def test_link_chat_returns_record_with_telegram_user_id(self):
        record = await self.players.link_chat_to_game(-1001, self.game.id, 555, "ali")
        self.assertEqual(record.telegram_user_id, 555)
        self.assertEqual(record.game_name, "WW2")
        self.assertTrue(record.active)

    async def test_get_by_chat_and_find_membership_and_lists(self):
        await self.players.link_chat_to_game(-1001, self.game.id, 555, "ali")

        by_chat = await self.players.get_by_chat(-1001)
        self.assertIsNotNone(by_chat)
        self.assertEqual(by_chat.telegram_user_id, 555)

        member = await self.players.find_membership(self.game.id, 555)
        self.assertIsNotNone(member)
        self.assertEqual(member.private_chat_id, -1001)
        self.assertIsNone(await self.players.find_membership(self.game.id, 999))

        self.assertEqual(len(await self.players.list_all()), 1)
        self.assertEqual(len(await self.players.list_by_game(self.game.id)), 1)

    async def test_identity_updates_are_visible_on_next_read(self):
        record = await self.players.link_chat_to_game(-1001, self.game.id, 555, None)
        await self.players.update_display_name(record.id, "علی")
        await self.players.update_country(record.id, "ایران")
        await self.players.set_active(record.id, False)

        fresh = await self.players.get_by_chat(-1001)
        self.assertEqual((fresh.display_name, fresh.country_or_faction, fresh.active),
                         ("علی", "ایران", False))

    async def test_same_user_can_join_two_games_in_two_chats(self):
        other = await self.games.create("Cold War")
        a = await self.players.link_chat_to_game(-1001, self.game.id, 555, "ali")
        b = await self.players.link_chat_to_game(-1002, other.id, 555, "ali")
        self.assertNotEqual(a.id, b.id)
        self.assertEqual(a.player_id, b.player_id)


if __name__ == "__main__":
    unittest.main()
