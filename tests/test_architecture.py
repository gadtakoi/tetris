import pkgutil
import subprocess
import sys
from pathlib import Path

import tetris

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_logic_does_not_import_pygame():
    modules = [f"tetris.{m.name}" for m in pkgutil.iter_modules(tetris.__path__)]
    assert modules, "no tetris modules found"
    code = (
        "import importlib, sys\n"
        f"for name in {modules!r}:\n"
        "    importlib.import_module(name)\n"
        "assert not any(m == 'pygame' or m.startswith('pygame.') for m in sys.modules), "
        "'pygame was imported'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
