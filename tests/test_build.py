"""Builds "SEVA Tetris.exe" and runs it headless. Slow, so only with TETRIS_BUILD_TEST=1."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXE_NAME = "SEVA Tetris.exe"

pytestmark = pytest.mark.skipif(
    os.environ.get("TETRIS_BUILD_TEST") != "1",
    reason="building the exe takes minutes; set TETRIS_BUILD_TEST=1 to run it",
)


def test_built_exe_runs_standalone(tmp_path):
    stale = PROJECT_ROOT / "dist" / "tetris.exe"  # as if left by a build before the rename
    stale.parent.mkdir(exist_ok=True)
    stale.write_bytes(b"")
    build = subprocess.run(
        [sys.executable, "build_exe.py"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=600,
    )
    assert build.returncode == 0, build.stdout[-2000:] + build.stderr[-2000:]
    built = PROJECT_ROOT / "dist" / EXE_NAME
    assert built.is_file()
    assert not stale.exists()

    exe_dir = tmp_path / "exe"
    exe_dir.mkdir()
    exe = Path(shutil.copy2(built, exe_dir / EXE_NAME))
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
