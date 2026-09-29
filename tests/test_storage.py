from pathlib import Path

from tetris.highscores import Entry, HighScores
from tetris_ui import storage
from tetris_ui.settings import Settings


def test_save_and_load(tmp_path):
    path = tmp_path / "highscores.json"
    table = HighScores()
    table.add(Entry("Иван", 1200, 13, 1))
    assert storage.save(table, path)
    assert storage.load(path).entries == (Entry("Иван", 1200, 13, 1),)
    assert "Иван" in path.read_text(encoding="utf-8")


def test_missing_file_gives_empty_table_and_save_creates_folder(tmp_path):
    path = tmp_path / "new" / "dir" / "highscores.json"
    assert storage.load(path).entries == ()
    table = HighScores()
    table.add(Entry("A", 10, 0, 0))
    assert storage.save(table, path)
    assert path.exists()
    assert list(path.parent.iterdir()) == [path]  # no temporary files left behind


def test_corrupted_file_gives_empty_table(tmp_path):
    path = tmp_path / "highscores.json"
    path.write_text("not json", encoding="utf-8")
    assert storage.load(path).entries == ()


def test_undecodable_file_gives_empty_table(tmp_path):
    path = tmp_path / "highscores.json"
    path.write_bytes(b"\xff\xfe\x00garbage")
    assert storage.load(path).entries == ()


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
    table = HighScores()
    table.add(Entry("Иван", 1200, 13, 1))
    assert storage.save(table, storage.high_scores_path())
    assert storage.load(folder / "highscores.json").entries == (Entry("Иван", 1200, 13, 1),)


def test_old_tetris_folder_is_neither_read_nor_changed(monkeypatch, tmp_path):
    monkeypatch.delenv("TETRIS_DATA_DIR", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    old = tmp_path / "tetris"
    old.mkdir()
    old_table = HighScores()
    old_table.add(Entry("Иван", 1200, 13, 1))
    (old / "highscores.json").write_text(old_table.to_json(), encoding="utf-8")
    (old / "settings.json").write_text('{"version": 1, "language": "ru"}', encoding="utf-8")
    before = {path.name: path.read_bytes() for path in old.iterdir()}

    assert storage.load(storage.high_scores_path()).entries == ()
    assert storage.load_settings(storage.settings_path()) == Settings()

    table = HighScores()
    table.add(Entry("Ann", 10, 0, 0))
    assert storage.save(table, storage.high_scores_path())
    assert storage.save_settings(Settings(music_on=False), storage.settings_path())
    assert {path.name: path.read_bytes() for path in old.iterdir()} == before


def test_save_failure_is_reported_not_raised(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not storage.save(HighScores(), blocker / "highscores.json")
    assert "could not save" in capsys.readouterr().err


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
