"""
Persian admin-command parsing.

This module has zero Telegram API dependencies on purpose, so the parsing
logic can be unit-tested in isolation without python-telegram-bot installed
(see tests/test_identity.py).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from constants import (
    CMD_ACTIVATE,
    CMD_DEACTIVATE,
    CMD_INFO,
    CMD_SET_COUNTRY,
    CMD_SET_NAME,
)

# Arabic keyboards type ي / ى / ك instead of the Persian ی / ک. They look
# identical on screen but are different code points, so a naive string
# comparison silently fails. This table is strictly 1:1 (same length), which
# lets us match on the translated text yet slice the value from the original.
_ARABIC_TO_PERSIAN = str.maketrans({"\u064A": "\u06CC", "\u0649": "\u06CC", "\u0643": "\u06A9"})

# Invisible bidi/BOM marks that Telegram clients and RTL keyboards often
# add around Persian text. str.strip() does NOT remove them.
_INVISIBLE_EDGE_CHARS = "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff"
_EDGE_RE = re.compile(rf"^[\s{_INVISIBLE_EDGE_CHARS}]+|[\s{_INVISIBLE_EDGE_CHARS}]+$")


def _compile(command: str, *, takes_value: bool) -> "re.Pattern[str]":
    """Match the command words separated by any whitespace, then (optionally) a value.

    Requiring whitespace (or end of text) after the command prevents
    "تنظیم کشورها" from being read as the command plus the value "ها".
    """
    canonical = command.translate(_ARABIC_TO_PERSIAN)
    words = r"\s+".join(re.escape(w) for w in canonical.split())
    tail = r"(?:\s+(?P<value>.*))?" if takes_value else ""
    return re.compile(rf"^{words}{tail}$", re.DOTALL)


_SET_COUNTRY_RE = _compile(CMD_SET_COUNTRY, takes_value=True)
_SET_NAME_RE = _compile(CMD_SET_NAME, takes_value=True)
_ACTIVATE_RE = _compile(CMD_ACTIVATE, takes_value=False)
_DEACTIVATE_RE = _compile(CMD_DEACTIVATE, takes_value=False)
_INFO_RE = _compile(CMD_INFO, takes_value=False)


@dataclass
class ParsedCommand:
    action: str  # "set_country" | "set_name" | "activate" | "deactivate" | "info"
    value: Optional[str] = None


def _value_from(match: "re.Match[str]", original: str) -> Optional[str]:
    if match.group("value") is None:
        return None
    # Slice from the ORIGINAL text so the stored value is exactly what the
    # admin typed (only the command words are matched leniently).
    value = _EDGE_RE.sub("", original[match.start("value"):match.end("value")])
    return value or None


def parse_admin_command(text: str) -> Optional[ParsedCommand]:
    """
    Parse a possible Persian admin command from free text.

    Returns None if the text does not match any known command - callers
    should treat that as "not a command" (e.g. ordinary chat), not an error.
    """
    original = _EDGE_RE.sub("", unicodedata.normalize("NFC", text))
    matchable = original.translate(_ARABIC_TO_PERSIAN)

    for action, pattern in (("set_country", _SET_COUNTRY_RE), ("set_name", _SET_NAME_RE)):
        m = pattern.match(matchable)
        if m:
            value = _value_from(m, original)
            return ParsedCommand(action, value) if value else None

    if _ACTIVATE_RE.match(matchable):
        return ParsedCommand("activate")
    if _DEACTIVATE_RE.match(matchable):
        return ParsedCommand("deactivate")
    if _INFO_RE.match(matchable):
        return ParsedCommand("info")

    return None
