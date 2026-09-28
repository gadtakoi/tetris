"""Builds tetris_shmetris.exe and runs it headless. Slow, so only with TETRIS_BUILD_TEST=1."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tetris_ui import GAME_TITLE, __version__
from tetris_ui.layout import VERSION_TEXT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXE_NAME = "tetris_shmetris.exe"
STALE_EXE = PROJECT_ROOT / "dist" / "tetris.exe"  # left by builds before the game got its name

pytestmark = pytest.mark.skipif(
    os.environ.get("TETRIS_BUILD_TEST") != "1",
    reason="building the exe takes minutes; set TETRIS_BUILD_TEST=1 to run it",
)


@pytest.fixture(scope="module")
def built_exe() -> Path:
    """Build the exe once for this module; the build also removes a stale tetris.exe."""
    STALE_EXE.parent.mkdir(exist_ok=True)
    STALE_EXE.write_bytes(b"")  # as if left by a build before the game got its name
    build = subprocess.run(
        [sys.executable, "build_exe.py"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=600,
    )
    assert build.returncode == 0, build.stdout[-2000:] + build.stderr[-2000:]
    built = PROJECT_ROOT / "dist" / EXE_NAME
    assert built.is_file()
    assert not STALE_EXE.exists()
    assert sorted(p.name for p in built.parent.glob("*.exe")) == [EXE_NAME]
    return built


def test_built_exe_runs_standalone(built_exe, tmp_path):
    exe_dir = tmp_path / "exe"
    exe_dir.mkdir()
    exe = Path(shutil.copy2(built_exe, exe_dir / EXE_NAME))
    env = dict(
        os.environ,
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        TETRIS_DATA_DIR=str(tmp_path / "data"),
    )
    result = subprocess.run(
        [str(exe), "--max-frames", "30"],
        cwd=exe_dir, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert [p.name for p in exe_dir.iterdir()] == [EXE_NAME]


def test_built_exe_has_the_version(built_exe):
    script = (
        f"$v = (Get-Item -LiteralPath '{built_exe}').VersionInfo; "
        "$v.FileVersion; $v.ProductVersion; $v.ProductName; $v.OriginalFilename; "
        "$v.FileDescription"
    )
    info = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=60,
    )
    assert info.returncode == 0, info.stderr
    file_version, product_version, product, original, description = info.stdout.splitlines()
    assert (file_version, product_version) == (f"{__version__}.0", __version__)
    assert (product, original, description) == (GAME_TITLE, EXE_NAME, GAME_TITLE)
    assert GAME_TITLE == "Tetris Shmetris"
    assert f"v{product_version}" == VERSION_TEXT  # the main menu shows the same number
