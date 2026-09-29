"""Builds the game for this system and runs it headless. Slow, so only with
TETRIS_BUILD_TEST=1."""

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import build_exe
from tetris_ui import GAME_TITLE, __version__
from tetris_ui.layout import VERSION_TEXT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXE_NAME = "tetris_shmetris.exe"
STALE_EXE = PROJECT_ROOT / "dist" / "tetris.exe"  # left by builds before the game got its name
BUILT = build_exe.built_path()  # the exe, the app or the file, by the system

pytestmark = pytest.mark.skipif(
    os.environ.get("TETRIS_BUILD_TEST") != "1",
    reason="building the game takes minutes; set TETRIS_BUILD_TEST=1 to run it",
)


@pytest.fixture(scope="module")
def built() -> Path:
    """Build the game once for this module; on Windows the build also removes a stale
    tetris.exe."""
    STALE_EXE.parent.mkdir(exist_ok=True)
    STALE_EXE.write_bytes(b"")  # as if left by a build before the game got its name
    build = subprocess.run(
        [sys.executable, "build_exe.py"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=600,
    )
    assert build.returncode == 0, build.stdout[-2000:] + build.stderr[-2000:]
    assert BUILT.exists()
    assert not STALE_EXE.exists()
    if sys.platform == "win32":
        assert sorted(p.name for p in BUILT.parent.glob("*.exe")) == [EXE_NAME]
    return BUILT


def copy_alone(built: Path, folder: Path) -> Path:
    """Copy the build into an empty folder and return the program to run in the copy."""
    folder.mkdir()
    if built.is_dir():  # the macOS app: its program is inside the bundle
        app = Path(shutil.copytree(built, folder / built.name, symlinks=True))
        return app / "Contents" / "MacOS" / build_exe.EXE_NAME
    return Path(shutil.copy2(built, folder / built.name))


def run_headless(program: Path, data_dir: Path, *args: str) -> subprocess.CompletedProcess:
    """Run the built game without a screen or sound for 30 frames."""
    env = dict(
        os.environ,
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        TETRIS_DATA_DIR=str(data_dir),
    )
    return subprocess.run(
        [str(program), *args, "--max-frames", "30"],
        cwd=program.parent, env=env, capture_output=True, text=True, timeout=30,
    )


def test_built_game_runs_standalone(built, tmp_path):
    folder = tmp_path / "copy"
    program = copy_alone(built, folder)
    result = run_headless(program, tmp_path / "data")
    assert result.returncode == 0, result.stderr
    assert [p.name for p in folder.iterdir()] == [built.name]


def test_built_game_runs_the_sound_check(built, tmp_path):
    folder = tmp_path / "copy"
    program = copy_alone(built, folder)
    data_dir = tmp_path / "data"
    result = run_headless(program, data_dir, "--sound-check")
    assert result.returncode == 0, result.stderr
    assert [p.name for p in folder.iterdir()] == [built.name]
    assert [p.name for p in data_dir.iterdir()] == ["sound-check.json"]


@pytest.mark.skipif(sys.platform != "win32", reason="the version resource is Windows only")
def test_built_exe_has_the_version(built):
    script = (
        f"$v = (Get-Item -LiteralPath '{built}').VersionInfo; "
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


@pytest.mark.skipif(sys.platform != "darwin", reason="Info.plist is macOS only")
def test_built_app_has_the_version_and_a_valid_signature(built):
    info = plistlib.loads((built / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleShortVersionString"] == info["CFBundleVersion"] == __version__
    assert info["CFBundleName"] == info["CFBundleDisplayName"] == GAME_TITLE
    assert info["CFBundleIdentifier"] == build_exe.BUNDLE_ID
    assert info["CFBundleExecutable"] == build_exe.EXE_NAME
    assert f"v{__version__}" == VERSION_TEXT
    check = subprocess.run(
        ["codesign", "--verify", "--strict", str(built)], capture_output=True, text=True,
    )
    assert check.returncode == 0, check.stderr
