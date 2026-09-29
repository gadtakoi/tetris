"""High score table rules: ordering, qualification, player names and the records that
go to the file (the file itself, its format and its signature are tetris_ui.storage's)."""

from __future__ import annotations

from dataclasses import dataclass

MAX_ENTRIES = 10
MAX_NAME_LENGTH = 10
DEFAULT_NAME = "PLAYER"

_EXTRA_NAME_CHARS = " -_"


@dataclass(frozen=True)
class Entry:
    """One result in the table: player name, score, cleared lines and level reached."""

    name: str
    score: int
    lines: int
    level: int


class HighScores:
    """The best results, at most MAX_ENTRIES of them, highest score first.

    A result that ties an existing score goes below it, so earlier results keep their
    place. Entries given to the constructor are inserted in order and cut to the maximum.
    """

    def __init__(self, entries: tuple[Entry, ...] = ()) -> None:
        self._entries: list[Entry] = []
        for entry in entries:
            self._insert(entry)
        del self._entries[MAX_ENTRIES:]

    @property
    def entries(self) -> tuple[Entry, ...]:
        """The entries, best first."""
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

    def to_records(self) -> list[dict]:
        """The entries as plain records with name, score, lines and level, best first."""
        return [
            {"name": e.name, "score": e.score, "lines": e.lines, "level": e.level}
            for e in self._entries
        ]

    @classmethod
    def from_records(cls, raw: object) -> HighScores:
        """A table from records read back from a file: anything but a list gives an empty
        table, and invalid records are skipped."""
        if not isinstance(raw, list):
            return cls()
        entries = [e for e in map(_parse_entry, raw) if e is not None]
        entries.sort(key=lambda e: e.score, reverse=True)  # stable: file order breaks ties
        return cls(tuple(entries))

    def _insert(self, entry: Entry) -> int:
        """Insert after every entry with an equal or higher score, so earlier results
        stay above; return the 1-based place."""
        index = 0
        while index < len(self._entries) and self._entries[index].score >= entry.score:
            index += 1
        self._entries.insert(index, entry)
        return index + 1


def _parse_entry(raw: object) -> Entry | None:
    """An Entry from one raw record, or None if any field is missing or invalid."""
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
    """Whether ch may appear in a player name: a letter of any alphabet, a digit, space, "-" or "_"."""
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
    """The name to store: the typed name trimmed, or DEFAULT_NAME if nothing is left."""
    return name.strip() or DEFAULT_NAME
