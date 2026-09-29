import json
import re
from pathlib import Path

import pytest

from tetris.highscores import Entry, HighScores
from tetris_ui import signing, storage
from tetris_ui.settings import Settings

ID = "0123456789abcdef0123456789abcdef"
OTHER_ID = "fedcba9876543210fedcba9876543210"
HEX32 = re.compile(r"[0-9a-f]{32}")


def ivan_table() -> HighScores:
    table = HighScores()
    table.add(Entry("Иван", 1200, 13, 1))
    return table


def test_save_and_load(tmp_path):
    path = tmp_path / "highscores.json"
    assert storage.save(ivan_table(), path, ID)
    assert storage.load(path, ID).entries == (Entry("Иван", 1200, 13, 1),)
    assert "Иван" in path.read_text(encoding="utf-8")


def test_missing_file_gives_empty_table_and_save_creates_folder(tmp_path, capsys):
    path = tmp_path / "new" / "dir" / "highscores.json"
    assert storage.load(path, ID).entries == ()
    table = HighScores()
    table.add(Entry("A", 10, 0, 0))
    assert storage.save(table, path, ID)
    assert path.exists()
    assert list(path.parent.iterdir()) == [path]  # no temporary files left behind
    assert capsys.readouterr().err == ""  # a first launch is no reason to warn


@pytest.mark.parametrize("text", ["not json", "[1, 2, 3]"])
def test_malformed_file_gives_empty_table_silently(tmp_path, capsys, text):
    path = tmp_path / "highscores.json"
    path.write_text(text, encoding="utf-8")
    assert storage.load(path, ID).entries == ()
    assert capsys.readouterr().err == ""


def test_undecodable_file_gives_empty_table(tmp_path):
    path = tmp_path / "highscores.json"
    path.write_bytes(b"\xff\xfe\x00garbage")
    assert storage.load(path, ID).entries == ()


def test_data_dir_override(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path))
    assert storage.data_dir() == tmp_path
    assert storage.high_scores_path() == tmp_path / "highscores.json"


def test_data_dir_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv("TETRIS_DATA_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert storage.data_dir() == tmp_path / "tetris_shmetris"


def test_data_dir_without_appdata(monkeypatch):
    monkeypatch.delenv("TETRIS_DATA_DIR", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    assert storage.data_dir() == Path.home() / ".local" / "share" / "tetris_shmetris"


def test_every_data_file_goes_to_the_tetris_shmetris_folder(monkeypatch, tmp_path):
    monkeypatch.delenv("TETRIS_DATA_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    folder = tmp_path / "tetris_shmetris"
    assert storage.high_scores_path() == folder / "highscores.json"
    assert storage.settings_path() == folder / "settings.json"
    assert storage.sound_check_path() == folder / "sound-check.json"
    assert storage.install_id_path() == folder / "install-id"
    assert storage.save(ivan_table(), storage.high_scores_path(), ID)
    assert storage.load(folder / "highscores.json", ID).entries == (Entry("Иван", 1200, 13, 1),)


def test_old_tetris_folder_is_neither_read_nor_changed(monkeypatch, tmp_path):
    monkeypatch.delenv("TETRIS_DATA_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    old = tmp_path / "tetris"
    # Signed for the same installation, so only the folder can keep it from loading.
    assert storage.save(ivan_table(), old / "highscores.json", ID)
    (old / "settings.json").write_text('{"version": 1, "language": "ru"}', encoding="utf-8")
    before = {path.name: path.read_bytes() for path in old.iterdir()}

    assert storage.load(storage.high_scores_path(), ID).entries == ()
    assert storage.load_settings(storage.settings_path()) == Settings()

    table = HighScores()
    table.add(Entry("Ann", 10, 0, 0))
    assert storage.save(table, storage.high_scores_path(), ID)
    assert storage.save_settings(Settings(music_on=False), storage.settings_path())
    assert {path.name: path.read_bytes() for path in old.iterdir()} == before


def test_save_failure_is_reported_not_raised(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not storage.save(HighScores(), blocker / "highscores.json", ID)
    assert "could not save" in capsys.readouterr().err


# --- Installation ID -------------------------------------------------------


def test_missing_install_id_is_created(tmp_path):
    path = tmp_path / "install-id"
    install_id = storage.load_install_id(path)
    assert HEX32.fullmatch(install_id)
    assert path.read_text(encoding="utf-8") == install_id + "\n"
    assert storage.load_install_id(path) == install_id  # the next launch keeps it


def test_saved_install_id_is_used_and_left_alone(tmp_path):
    path = tmp_path / "install-id"
    path.write_bytes(ID.encode("ascii") + b"\n")
    before = path.stat().st_mtime_ns
    assert storage.load_install_id(path) == ID
    assert path.read_bytes() == ID.encode("ascii") + b"\n"
    assert path.stat().st_mtime_ns == before
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("content", ["hello", ID.upper(), ID[:16], ""])
def test_broken_install_id_is_replaced(tmp_path, content):
    path = tmp_path / "install-id"
    path.write_text(content, encoding="utf-8")
    install_id = storage.load_install_id(path)
    assert HEX32.fullmatch(install_id)
    assert path.read_text(encoding="utf-8") == install_id + "\n"


def test_install_id_that_cannot_be_saved_is_still_used(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    install_id = storage.load_install_id(blocker / "install-id")  # a folder inside a file
    assert HEX32.fullmatch(install_id)
    assert "could not save installation ID" in capsys.readouterr().err


def test_install_id_lives_next_to_the_high_scores(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path))
    assert storage.install_id_path() == tmp_path / "install-id"
    assert storage.install_id_path().parent == storage.high_scores_path().parent


# --- Signed table ----------------------------------------------------------


def saved_table(tmp_path, install_id: str = ID) -> Path:
    path = tmp_path / "highscores.json"
    assert storage.save(ivan_table(), path, install_id)
    return path


def edit_file(path: Path, change) -> None:
    """Change the saved JSON by hand, as someone with a text editor would."""
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_saved_file_format(tmp_path):
    data = json.loads(saved_table(tmp_path).read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["entries"] == [{"name": "Иван", "score": 1200, "lines": 13, "level": 1}]
    assert re.fullmatch(r"[0-9a-f]{64}", data["sig"])
    assert data["sig"] == signing.signature(ID, data["entries"])


def test_reformatted_file_still_loads(tmp_path):
    path = saved_table(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True),
                    encoding="utf-8")
    assert storage.load(path, ID).entries == (Entry("Иван", 1200, 13, 1),)


def test_score_edited_by_hand_gives_empty_table_and_a_warning(tmp_path, capsys):
    path = saved_table(tmp_path)
    edit_file(path, lambda data: data["entries"][0].update(score=999999))
    assert storage.load(path, ID).entries == ()
    err = capsys.readouterr().err
    assert "failed the integrity check" in err
    assert str(path) in err


def test_file_from_another_installation_gives_empty_table(tmp_path):
    path = saved_table(tmp_path, ID)
    assert storage.load(path, OTHER_ID).entries == ()


def test_file_of_the_old_format_gives_empty_table(tmp_path, capsys):
    path = tmp_path / "highscores.json"
    old = {"version": 1, "entries": [{"name": "A", "score": 100, "lines": 1, "level": 0}]}
    path.write_text(json.dumps(old), encoding="utf-8")
    assert storage.load(path, ID).entries == ()
    assert "failed the integrity check" in capsys.readouterr().err


def test_removed_signature_gives_empty_table(tmp_path):
    path = saved_table(tmp_path)
    edit_file(path, lambda data: data.pop("sig"))
    assert storage.load(path, ID).entries == ()


def test_signature_that_is_not_a_string_gives_empty_table(tmp_path):
    path = saved_table(tmp_path)
    edit_file(path, lambda data: data.update(sig=12345))
    assert storage.load(path, ID).entries == ()


def test_loading_a_forged_file_leaves_it_as_it_is(tmp_path):
    path = saved_table(tmp_path)
    edit_file(path, lambda data: data["entries"][0].update(score=999999))
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    assert storage.load(path, ID).entries == ()
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


def test_new_record_after_a_forgery_is_saved_signed(tmp_path):
    path = saved_table(tmp_path)
    edit_file(path, lambda data: data["entries"][0].update(score=999999))
    table = storage.load(path, ID)
    table.add(Entry("Ann", 500, 5, 0))
    assert storage.save(table, path, ID)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["entries"] == [{"name": "Ann", "score": 500, "lines": 5, "level": 0}]
    assert signing.is_valid(data["sig"], ID, data["entries"])
    assert storage.load(path, ID).entries == (Entry("Ann", 500, 5, 0),)


def test_lost_install_id_gives_empty_table(tmp_path):
    id_path = tmp_path / "install-id"
    first = storage.load_install_id(id_path)
    path = saved_table(tmp_path, first)
    id_path.unlink()
    second = storage.load_install_id(id_path)
    assert second != first
    assert storage.load(path, second).entries == ()


# --- Sound settings --------------------------------------------------------


def test_save_and_load_settings(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(music_on=False, sound_on=True, music_volume=70)
    assert storage.save_settings(settings, path)
    assert storage.load_settings(path) == settings
    assert list(tmp_path.iterdir()) == [path]  # no temporary files left behind


def test_missing_settings_give_defaults(tmp_path):
    assert storage.load_settings(tmp_path / "settings.json") == Settings()


def test_corrupted_settings_give_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    assert storage.load_settings(path) == Settings()


def test_settings_live_next_to_high_scores(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path))
    assert storage.settings_path() == tmp_path / "settings.json"
    assert storage.settings_path().parent == storage.high_scores_path().parent


def test_settings_save_failure_is_reported_not_raised(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not storage.save_settings(Settings(), blocker / "settings.json")
    assert "could not save settings" in capsys.readouterr().err


# --- Sound check report ----------------------------------------------------


def test_sound_check_report_next_to_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path))
    assert storage.sound_check_path() == tmp_path / "sound-check.json"
    assert storage.sound_check_path().parent == storage.settings_path().parent


def test_save_sound_check_replaces_the_last_report(tmp_path):
    path = tmp_path / "sound-check.json"
    assert storage.save_sound_check('{"version": 1, "items": ["старый"]}', path)
    assert storage.save_sound_check('{"version": 1, "items": ["новый"]}', path)
    assert path.read_text(encoding="utf-8") == '{"version": 1, "items": ["новый"]}'
    assert list(tmp_path.iterdir()) == [path]  # no temporary files left behind


def test_sound_check_save_failure_is_reported_not_raised(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not storage.save_sound_check("{}", blocker / "sound-check.json")
    assert "sound check report" in capsys.readouterr().err
