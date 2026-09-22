"""
Unit tests for Persian admin-command parsing.

These test pure logic only - no Telegram API / network access needed.

Run with:  python3 -m unittest discover -s tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.identity import parse_admin_command


class TestParseAdminCommand(unittest.TestCase):
    def test_set_country_basic(self):
        result = parse_admin_command("تنظیم کشور ایران")
        self.assertIsNotNone(result)
        self.assertEqual(result.action, "set_country")
        self.assertEqual(result.value, "ایران")

    def test_set_country_with_extra_whitespace(self):
        result = parse_admin_command("  تنظیم کشور   باد  ")
        self.assertEqual(result.action, "set_country")
        self.assertEqual(result.value, "باد")

    def test_set_country_english_value(self):
        result = parse_admin_command("تنظیم کشور Kingdom of Nothing")
        self.assertEqual(result.value, "Kingdom of Nothing")

    def test_set_name_basic(self):
        result = parse_admin_command("تنظیم اسم علی")
        self.assertEqual(result.action, "set_name")
        self.assertEqual(result.value, "علی")

    def test_set_name_multiword_value(self):
        result = parse_admin_command("تنظیم اسم پادشاه باد")
        self.assertEqual(result.value, "پادشاه باد")

    def test_set_country_without_value_is_invalid(self):
        self.assertIsNone(parse_admin_command("تنظیم کشور"))
        self.assertIsNone(parse_admin_command("تنظیم کشور   "))

    def test_set_name_without_value_is_invalid(self):
        self.assertIsNone(parse_admin_command("تنظیم اسم"))

    def test_activate(self):
        result = parse_admin_command("فعال")
        self.assertEqual(result.action, "activate")
        self.assertIsNone(result.value)

    def test_deactivate(self):
        result = parse_admin_command("غیرفعال")
        self.assertEqual(result.action, "deactivate")

    def test_info(self):
        result = parse_admin_command("اطلاعات")
        self.assertEqual(result.action, "info")

    def test_unrelated_text_returns_none(self):
        self.assertIsNone(parse_admin_command("Hello, we entered the city."))
        self.assertIsNone(parse_admin_command("سلام"))

    def test_activate_with_trailing_text_is_not_matched(self):
        # "فعال" must match *exactly* - trailing text means this is just
        # normal roleplay content, not the activation command.
        self.assertIsNone(parse_admin_command("فعال سازی نیرو ها"))

    # --- robustness for real-world Persian keyboard input -----------------
    def test_arabic_kaf_and_yeh_are_accepted_in_command_words(self):
        # U+0643 (Arabic kaf) looks identical to U+06A9 (Persian kaf).
        result = parse_admin_command("تنظیم \u0643شور ایران")
        self.assertEqual(result.action, "set_country")
        self.assertEqual(parse_admin_command("غ\u064Aرفعال").action, "deactivate")

    def test_value_is_stored_exactly_as_typed(self):
        # Only the command words are matched leniently; the value is untouched.
        typed = "\u0643شور \u064Aمن"
        result = parse_admin_command("تنظیم اسم " + typed)
        self.assertEqual(result.value, typed)

    def test_zwnj_inside_value_is_preserved(self):
        result = parse_admin_command("تنظیم اسم می\u200cخواهم")
        self.assertEqual(result.value, "می\u200cخواهم")

    def test_invisible_bidi_marks_at_edges_are_ignored(self):
        self.assertEqual(parse_admin_command("\u200fتنظیم کشور ایران").value, "ایران")
        self.assertEqual(parse_admin_command("فعال\u200f").action, "activate")

    def test_extra_internal_whitespace_between_command_words(self):
        self.assertEqual(parse_admin_command("تنظیم   کشور ایران").value, "ایران")

    def test_command_must_end_at_a_word_boundary(self):
        # Previously parsed as set_country with value "ها" / set_name with "ش".
        self.assertIsNone(parse_admin_command("تنظیم کشورها"))
        self.assertIsNone(parse_admin_command("تنظیم اسمش"))


if __name__ == "__main__":
    unittest.main()
