import os
import subprocess
import sys
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest

from tetris_ui import cli

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path))
    return tmp_path


def test_run_with_max_frames(data_dir):
    assert cli.run(["--max-frames", "3"]) == 0


@pytest.mark.parametrize("value", ["0", "-5", "abc", "2.5"])
def test_invalid_max_frames_exits_before_any_window(value, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.run(["--max-frames", value])
    assert exc.value.code != 0
    assert "--max-frames" in capsys.readouterr().err
    pygame = sys.modules.get("pygame")
    assert pygame is None or not pygame.display.get_init()


def test_help_names_the_game(capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.parse_args(["--help"])
    assert exit_.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: Tetris Shmetris")
    assert "Tetris Shmetris: classic Tetris." in out


def test_no_arguments_means_no_frame_limit():
    assert cli.parse_args([]).max_frames is None


def test_warn_writes_to_stderr(capsys):
    cli.warn("careful")
    assert capsys.readouterr().err == "tetris: careful\n"


def test_warn_without_stderr(monkeypatch):
    monkeypatch.setattr(sys, "stderr", None)
    cli.warn("nobody listens")  # a windowed exe has no stderr; must not raise


def run_module(*args: str, tmp_path: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
               TETRIS_DATA_DIR=str(tmp_path))
    return subprocess.run(
        [sys.executable, "-m", "tetris_ui", *args],
        cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=60,
    )


def test_module_runs_given_frames(tmp_path):
    result = run_module("--max-frames", "3", tmp_path=tmp_path)
    assert result.returncode == 0, result.stderr


def test_module_rejects_zero_frames(tmp_path):
    result = run_module("--max-frames", "0", tmp_path=tmp_path)
    assert result.returncode != 0
