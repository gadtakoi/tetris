import json
import subprocess
import sys
from pathlib import Path

import pytest

from tetris_ui import layout, soundcheck, synth
from tetris_ui.soundcheck import ITEMS, MUSIC, CheckKey, Playback, SoundCheck
from tetris_ui.texts import RU

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOVE_REPEAT = 8  # index of item 9, "Move with autorepeat"
LAST = len(ITEMS) - 1  # index of item 13, the music

# The table "Состав проверки" from the sound-check spec: (id, title, description).
SPEC_ITEMS = [
    ("move", "Move", "Piece moved left or right"),
    ("rotate", "Rotate", "Piece turned"),
    ("hold", "Hold piece", "Piece put on hold"),
    ("lock", "Lock", "Piece locked, no lines cleared"),
    ("clear", "Line clear", "One to three lines cleared"),
    ("tetris", "Tetris", "Four lines cleared at once"),
    ("level_up", "Level up", "Level went up"),
    ("game_over", "Game over", "Game ended"),
    ("move_repeat", "Move with autorepeat", "Key held: 7 moves wall to wall"),
    ("clear_level_up", "Clear + level up", "Lines cleared, level went up"),
    ("tetris_level_up", "Tetris + level up", "Tetris, level went up"),
    ("lock_game_over", "Lock + game over", "Last piece locked, game over"),
    ("music", "Music", "Background melody in a loop"),
]
AUTOREPEAT_TIMES = [0, 170, 220, 270, 320, 370, 420]


def item(item_id: str) -> soundcheck.CheckItem:
    return next(entry for entry in ITEMS if entry.id == item_id)


# --- The items -------------------------------------------------------------


def test_thirteen_items_in_spec_order():
    assert [(i.id, i.title, i.description) for i in ITEMS] == SPEC_ITEMS


def test_single_effects_start_at_once():
    for entry in ITEMS[:8]:
        assert entry.cues == ((0, entry.id),)


def test_combinations_start_together():
    assert item("clear_level_up").cues == ((0, "clear"), (0, "level_up"))
    assert item("tetris_level_up").cues == ((0, "tetris"), (0, "level_up"))
    assert item("lock_game_over").cues == ((0, "lock"), (0, "game_over"))


def test_move_with_autorepeat_follows_the_normal_speed():
    assert item("move_repeat").cues == tuple((t, "move") for t in AUTOREPEAT_TIMES)


def test_music_item_plays_the_melody():
    assert item("music").cues == ((0, MUSIC),)


def test_every_cue_is_a_game_sound():
    cues = {cue for entry in ITEMS for _, cue in entry.cues}
    assert cues <= set(synth.EFFECTS) | {MUSIC}
    assert set(synth.EFFECTS) <= cues  # every effect of the game is checked


def test_soundcheck_module_does_not_import_pygame():
    code = "import sys, tetris_ui.soundcheck; assert 'pygame' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


# --- Choosing and playing ----------------------------------------------------


def check_on(index: int, **kwargs) -> SoundCheck:
    """A check with item `index` selected by Down presses; every start is played out."""
    check = SoundCheck(**kwargs)
    check.update(16)
    for _ in range(index):
        check.key_down(CheckKey.DOWN)
        check.update(16)
    return check


def cue_times(check: SoundCheck, dt: int, until_ms: int, cue: str) -> list[int]:
    """The item clock in each frame of dt ms (the first frame is moment 0) where `cue` starts."""
    times = []
    for frame in range(until_ms // dt + 1):
        if cue in check.update(dt).cues:
            times.append(frame * dt)
    return times


def test_first_item_plays_at_start():
    check = SoundCheck()
    assert check.index == 0 and check.item.title == "Move"
    assert check.update(700) == Playback(stop=True, cues=("move",))  # a long first frame
    assert check.update(16) == Playback()


def test_move_with_autorepeat_in_10_ms_frames():
    check = check_on(MOVE_REPEAT - 1)
    check.key_down(CheckKey.DOWN)
    assert cue_times(check, 10, 1000, "move") == AUTOREPEAT_TIMES


def test_move_with_autorepeat_in_16_ms_frames():
    check = check_on(MOVE_REPEAT - 1)
    check.key_down(CheckKey.DOWN)
    times = cue_times(check, 16, 1000, "move")
    assert len(times) == 7
    assert all(t <= at < t + 16 for t, at in zip(AUTOREPEAT_TIMES, times))


def test_simultaneous_sounds_start_in_one_frame():
    check = check_on(9)
    check.key_down(CheckKey.DOWN)  # item 11, "Tetris + level up"
    assert check.update(16) == Playback(stop=True, cues=("tetris", "level_up"))


def test_replay_drops_the_delayed_sounds_of_the_first_run():
    check = check_on(MOVE_REPEAT - 1)
    check.key_down(CheckKey.DOWN)
    assert cue_times(check, 10, 200, "move") == [0, 170]
    check.key_down(CheckKey.PLAY)
    assert check.update(10).stop
    later = cue_times(check, 10, 1000, "move")
    assert [0] + [t + 10 for t in later] == AUTOREPEAT_TIMES  # counted from the press


def test_leaving_the_music():
    check = check_on(LAST)
    check.key_down(CheckKey.UP)
    assert check.index == LAST - 1
    assert check.update(16) == Playback(stop=True, cues=("lock", "game_over"))


def test_down_goes_through_every_item():
    check = SoundCheck()
    heard = [check.update(16).cues]
    for _ in range(12):
        check.key_down(CheckKey.DOWN)
        heard.append(check.update(16).cues)
    assert check.index == LAST
    assert heard[-1] == (MUSIC,)
    assert all(check.played)
    assert heard == [tuple(dict.fromkeys(cue for t, cue in i.cues if t == 0)) for i in ITEMS]


@pytest.mark.parametrize(("index", "key"), [(0, CheckKey.UP), (LAST, CheckKey.DOWN)])
def test_list_ends_do_not_restart(index, key):
    check = check_on(index)
    check.update(1000)  # the item has finished
    check.key_down(key)
    assert check.index == index
    assert check.update(16) == Playback()


def test_replay_restarts_the_selected_item():
    check = check_on(3)
    check.key_down(CheckKey.PLAY)
    assert check.update(16) == Playback(stop=True, cues=("lock",))


def test_mark_and_unmark():
    check = check_on(3)
    check.key_down(CheckKey.MARK)
    assert check.marked == [i == 3 for i in range(len(ITEMS))]
    check.key_down(CheckKey.MARK)
    assert not any(check.marked)


def test_mark_does_not_interrupt_the_sound():
    check = check_on(LAST)
    check.key_down(CheckKey.MARK)
    assert check.update(16) == Playback()  # no stop: the music goes on
    assert check.marked[LAST]


def test_one_sound_of_an_effect_per_frame():
    check = check_on(MOVE_REPEAT - 1)
    check.key_down(CheckKey.DOWN)
    assert check.update(120).cues == ("move",)  # moment 0
    assert check.update(120) == Playback()  # 120 ms
    assert check.update(120).cues == ("move",)  # 240 ms: 170 and 220 are due, one sounds
    assert check.update(120).cues == ("move",)  # 360 ms: 270 and 320
    assert check.update(120).cues == ("move",)  # 480 ms: 370 and 420
    assert check.update(120) == Playback()


def test_escape_ends_the_check():
    check = SoundCheck()
    assert not check.exit_requested
    check.key_down(CheckKey.EXIT)
    assert check.exit_requested


def test_nothing_counts_as_played_without_a_sound_device():
    check = check_on(LAST, can_play=False)
    check.key_down(CheckKey.PLAY)
    assert not any(check.played)
    assert check.update(16).stop  # the schedule still runs; there is just nothing to hear


# --- The report --------------------------------------------------------------


def report_items(text: str) -> list[dict]:
    data = json.loads(text)
    assert data["version"] == 1 and set(data) == {"version", "items"}
    return data["items"]


def test_report_at_start():
    items = report_items(SoundCheck().report_json())
    assert [(i["number"], i["id"]) for i in items] == [
        (number, item_id) for number, (item_id, _, _) in enumerate(SPEC_ITEMS, start=1)
    ]
    assert [set(i) for i in items] == [{"number", "id", "played", "unpleasant"}] * 13
    assert [i["played"] for i in items] == [True] + [False] * 12
    assert not any(i["unpleasant"] for i in items)


def test_report_goes_out_on_every_change():
    reports: list[str] = []
    check = SoundCheck(on_report=reports.append)
    assert len(reports) == 1  # the new report of this check
    assert reports[0] == check.report_json()
    check.update(16)
    check.key_down(CheckKey.DOWN)  # item 2 heard for the first time
    assert len(reports) == 2
    check.key_down(CheckKey.UP)  # item 1 again
    check.key_down(CheckKey.PLAY)
    check.key_down(CheckKey.UP)  # the top of the list
    assert len(reports) == 2
    check.key_down(CheckKey.MARK)
    assert report_items(reports[-1])[0]["unpleasant"] is True
    check.key_down(CheckKey.MARK)
    assert report_items(reports[-1])[0]["unpleasant"] is False
    check.key_down(CheckKey.EXIT)
    assert len(reports) == 4
    assert reports[-1] == check.report_json()


def test_report_without_a_sound_device():
    reports: list[str] = []
    check = SoundCheck(can_play=False, on_report=reports.append)
    check.key_down(CheckKey.DOWN)
    check.key_down(CheckKey.UP)
    check.key_down(CheckKey.MARK)
    assert len(reports) == 2  # the start and the mark
    first = report_items(reports[-1])[0]
    assert (first["played"], first["unpleasant"]) == (False, True)
    assert not any(i["played"] for i in report_items(reports[-1]))


# --- The screen ----------------------------------------------------------------


def screen(check: SoundCheck, language: str = "en", has_audio: bool = True) -> dict:
    """The screen texts by role: {role: [(text, position, color), ...]}."""
    by_role: dict[str, list] = {}
    for text, pos, role, color in layout.sound_check_texts(check, language, has_audio):
        by_role.setdefault(role, []).append((text, pos, color))
    return by_role


def texts_of(check: SoundCheck, language: str = "en", has_audio: bool = True) -> list[str]:
    return [text for text, _, _, _ in layout.sound_check_texts(check, language, has_audio)]


def test_screen_at_start():
    shown = screen(SoundCheck())
    assert [text for text, _, _ in shown["title"]] == ["Sound check"]
    rows = shown["row"]
    assert [text for text, _, _ in rows] == [
        f"{number}. {title}" for number, (_, title, _) in enumerate(SPEC_ITEMS, start=1)
    ]
    assert [color for _, _, color in rows] == [(240, 240, 0)] + [layout.TEXT] * 12
    assert [text for text, _, _ in shown["note"]] == [
        "Piece moved left or right",
        "Volume: effects 100%, music 50%",
        "Marks are saved to sound-check.json",
    ]
    assert [text for text, _, _ in shown["hint"]] == [
        "Up / Down - choose, Space - play again", "X - unpleasant, Esc - exit",
    ]
    assert "mark" not in shown and "unpleasant" not in texts_of(SoundCheck())


def test_rows_go_down_the_screen_from_the_top_left():
    rows = screen(SoundCheck())["row"]
    assert [pos for _, pos, _ in rows] == [(40, 90 + 30 * i) for i in range(13)]


def test_marked_item_on_the_screen():
    check = check_on(3)
    check.key_down(CheckKey.MARK)
    check.key_down(CheckKey.DOWN)
    shown = screen(check)
    ((mark, mark_pos, mark_color),) = shown["mark"]
    row_pos = next(pos for text, pos, _ in shown["row"] if text == "4. Lock")
    assert mark == "unpleasant" and mark_color == layout.MARK_COLOR
    assert mark_pos[1] == row_pos[1] and mark_pos[0] > row_pos[0]  # to the right of its row
    highlighted = [text for text, _, color in shown["row"] if color == layout.HIGHLIGHT]
    assert highlighted == ["5. Line clear"]
    assert shown["note"][0][0] == "One to three lines cleared"


def test_screen_in_russian():
    texts = texts_of(SoundCheck(), "ru")
    for text in ("Проверка звуков", "1. Сдвиг", "9. Сдвиг с автоповтором", "13. Музыка",
                 "Громкость: эффекты 100%, музыка 50%",
                 "Вверх / Вниз - выбор, Пробел - ещё раз"):
        assert text in texts, text


def test_marked_item_in_russian():
    check = check_on(11)
    check.key_down(CheckKey.MARK)
    texts = texts_of(check, "ru")
    for text in ("12. Закрепление + конец игры", "неприятно",
                 "Последняя фигура закрепилась, конец игры", "X - неприятно, Esc - выход"):
        assert text in texts, text


@pytest.mark.parametrize(("language", "notice"), [("en", "No sound device"),
                                                  ("ru", "Нет звукового устройства")])
def test_no_sound_device_replaces_the_volume_line(language, notice):
    notes = [text for text, _, _ in screen(SoundCheck(can_play=False), language, False)["note"]]
    assert notes[1] == notice
    assert not any(note.startswith(("Volume", "Громкость")) for note in notes)


@pytest.mark.parametrize("has_audio", [True, False])
def test_every_text_is_translated(has_audio):
    check = SoundCheck()
    for index in range(len(ITEMS)):
        check.key_down(CheckKey.MARK)  # every item ends up marked
        texts = texts_of(check, "ru", has_audio)
        titles = [text.split(". ", 1)[1] for text, _, role, _ in
                  layout.sound_check_texts(check, "ru", has_audio) if role == "row"]
        left_english = (set(texts) | set(titles)) & set(RU)
        assert not left_english, (index, left_english)
        check.key_down(CheckKey.DOWN)
    assert all(check.marked)
