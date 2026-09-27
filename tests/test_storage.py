from pathlib import Path

from tetris.highscores import Entry, HighScores
from tetris_ui import storage


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
    assert storage.data_dir() == tmp_path / "tetris"


def test_data_dir_without_appdata(monkeypatch):
    monkeypatch.delenv("TETRIS_DATA_DIR", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    assert storage.data_dir() == Path.home() / ".local" / "share" / "tetris"


def test_save_failure_is_reported_not_raised(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not storage.save(HighScores(), blocker / "highscores.json")
    assert "could not save" in capsys.readouterr().err
