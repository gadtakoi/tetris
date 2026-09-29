import pytest

from tetris.highscores import (
    Entry,
    HighScores,
    append_to_name,
    final_name,
)


def entry(score: int, name: str = "P") -> Entry:
    return Entry(name, score, 0, 0)


def full_table(lowest: int = 500) -> HighScores:
    table = HighScores()
    for i in range(10):
        table.add(entry(lowest + 100 * (9 - i), f"P{i}"))
    return table


# --- Order and qualification -----------------------------------------------


def test_entries_are_ordered_by_score():
    table = HighScores()
    for score in (300, 1200, 40):
        table.add(entry(score))
    assert [e.score for e in table.entries] == [1200, 300, 40]


def test_earlier_entry_wins_a_tie():
    table = HighScores()
    table.add(entry(500, "ANNA"))
    table.add(entry(500, "BORIS"))
    assert [e.name for e in table.entries] == ["ANNA", "BORIS"]


def test_zero_score_never_qualifies():
    assert not HighScores().qualifies(0)
    with pytest.raises(ValueError):
        HighScores().add(entry(0))


def test_table_with_room_accepts_any_score():
    table = HighScores()
    for score in (1200, 300, 40):
        table.add(entry(score))
    assert table.add(entry(100)) == 3
    assert len(table.entries) == 4


def test_tie_with_last_of_full_table_does_not_qualify():
    table = full_table(lowest=500)
    assert table.entries[-1].score == 500
    assert not table.qualifies(500)


def test_better_score_pushes_out_the_last_entry():
    table = full_table(lowest=500)
    assert table.add(entry(501, "NEW")) == 10
    assert len(table.entries) == 10
    assert table.entries[-1] == entry(501, "NEW")
    assert all(e.score != 500 for e in table.entries)


# --- Player names ----------------------------------------------------------


def test_cyrillic_and_digits():
    assert final_name(append_to_name("", "Иван 2")) == "Иван 2"


def test_disallowed_characters_are_dropped():
    assert append_to_name("", "A!B@C") == "ABC"


def test_name_is_cut_at_ten_characters():
    assert append_to_name("", "ABCDEFGHIJKL") == "ABCDEFGHIJ"
    assert append_to_name("ABCDEFGHIJ", "K") == "ABCDEFGHIJ"


@pytest.mark.parametrize("typed", ["", "   "])
def test_empty_name_becomes_player(typed):
    assert final_name(append_to_name("", typed)) == "PLAYER"


def test_name_is_trimmed():
    assert final_name(" Ann ") == "Ann"


# --- Records ---------------------------------------------------------------


def test_records_round_trip():
    table = HighScores()
    table.add(Entry("Иван", 1200, 13, 1))
    table.add(Entry("Ann", 340, 3, 0))
    records = table.to_records()
    assert records == [
        {"name": "Иван", "score": 1200, "lines": 13, "level": 1},
        {"name": "Ann", "score": 340, "lines": 3, "level": 0},
    ]
    assert HighScores.from_records(records).entries == table.entries


def test_invalid_record_is_skipped():
    raw = [
        {"name": "GOOD", "score": 100, "lines": 1, "level": 0},
        {"name": "BAD", "score": "abc", "lines": 1, "level": 0},
    ]
    assert HighScores.from_records(raw).entries == (Entry("GOOD", 100, 1, 0),)


def test_only_best_ten_records_are_loaded():
    raw = [{"name": f"P{i}", "score": 10 * i, "lines": 0, "level": 0} for i in range(1, 13)]
    table = HighScores.from_records(raw)
    assert [e.score for e in table.entries] == [120, 110, 100, 90, 80, 70, 60, 50, 40, 30]


def test_equal_scores_keep_the_order_of_the_records():
    raw = [
        {"name": "LOW", "score": 10, "lines": 0, "level": 0},
        {"name": "ANNA", "score": 500, "lines": 0, "level": 0},
        {"name": "BORIS", "score": 500, "lines": 0, "level": 0},
    ]
    assert [e.name for e in HighScores.from_records(raw).entries] == ["ANNA", "BORIS", "LOW"]


@pytest.mark.parametrize("raw", [None, "nope", 42, {"entries": []}])
def test_anything_but_a_list_gives_an_empty_table(raw):
    assert HighScores.from_records(raw).entries == ()
