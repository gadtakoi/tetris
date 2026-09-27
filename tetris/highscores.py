"""High score table rules: ordering, qualification, player names and JSON form."""

from __future__ import annotations

import json
from dataclasses import dataclass

MAX_ENTRIES = 10
MAX_NAME_LENGTH = 10
DEFAULT_NAME = "PLAYER"
FORMAT_VERSION = 1

_EXTRA_NAME_CHARS = " -_"


@dataclass(frozen=True)
class Entry:
    name: str
    score: int
    lines: int
    level: int


class HighScores:
    def __init__(self, entries: tuple[Entry, ...] = ()) -> None:
        self._entries: list[Entry] = []
        for entry in entries:
            self._insert(entry)
        del self._entries[MAX_ENTRIES:]

    @property
    def entries(self) -> tuple[Entry, ...]:
        return tuple(self._entries)

    def qualifies(self, score: int) -> bool:
        """A result enters the table if it scores and beats the last of a full table."""
        if score <= 0:
            return False
        return len(self._entries) < MAX_ENTRIES or score > self._entries[-1].score

    def add(self, entry: Entry) -> int:
        """Insert a qualifying result and return its place, 1-10."""
        if not self.qualifies(entry.score):
            raise ValueError(f"score {entry.score} does not enter the table")
        place = self._insert(entry)
        del self._entries[MAX_ENTRIES:]
        return place

    def to_json(self) -> str:
        return json.dumps(
            {
                "version": FORMAT_VERSION,
                "entries": [
                    {"name": e.name, "score": e.score, "lines": e.lines, "level": e.level}
                    for e in self._entries
                ],
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str) -> HighScores:
        """Parse a saved table; anything unreadable yields an empty table."""
        try:
            data = json.loads(text)
        except ValueError:
            return cls()
        if not isinstance(data, dict) or data.get("version") != FORMAT_VERSION:
            return cls()
        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list):
            return cls()
        entries = [e for e in map(_parse_entry, raw_entries) if e is not None]
        entries.sort(key=lambda e: e.score, reverse=True)  # stable: file order breaks ties
        return cls(tuple(entries))

    def _insert(self, entry: Entry) -> int:
        # After every entry with an equal or higher score, so earlier results stay above.
        index = 0
        while index < len(self._entries) and self._entries[index].score >= entry.score:
            index += 1
        self._entries.insert(index, entry)
        return index + 1


def _parse_entry(raw: object) -> Entry | None:
    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    numbers = [raw.get(key) for key in ("score", "lines", "level")]
    if not isinstance(name, str) or not name or len(name) > MAX_NAME_LENGTH:
        return None
    if not all(type(n) is int and n >= 0 for n in numbers):
        return None
    return Entry(name, *numbers)


def is_name_char(ch: str) -> bool:
    return len(ch) == 1 and (ch.isalpha() or ch.isdigit() or ch in _EXTRA_NAME_CHARS)


def append_to_name(name: str, text: str) -> str:
    """Add the allowed characters of text to name, up to the maximum length."""
    for ch in text:
        if len(name) >= MAX_NAME_LENGTH:
            break
        if is_name_char(ch):
            name += ch
    return name


def final_name(name: str) -> str:
    return name.strip() or DEFAULT_NAME
