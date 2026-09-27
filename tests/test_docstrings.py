"""Every module, class, function and method of the game has a docstring."""

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SOURCES = sorted(
    [
        *PROJECT_ROOT.glob("tetris/*.py"),
        *PROJECT_ROOT.glob("tetris_ui/*.py"),
        PROJECT_ROOT / "build_exe.py",
        PROJECT_ROOT / "launcher.py",
    ]
)

DEFINITIONS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def missing_docstrings(path: Path) -> list[str]:
    """Places in one file without a docstring, as "file:line name"."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    name = path.relative_to(PROJECT_ROOT).as_posix()
    missing = [] if ast.get_docstring(tree) else [f"{name}:1 <module>"]
    for node in ast.walk(tree):
        # A constructor is described by its class docstring.
        if isinstance(node, DEFINITIONS) and node.name != "__init__":
            if not ast.get_docstring(node):
                missing.append(f"{name}:{node.lineno} {node.name}")
    return missing


def test_sources_are_found():
    assert len(SOURCES) > 10
    assert all(path.is_file() for path in SOURCES)


def test_everything_has_a_docstring():
    missing = [place for path in SOURCES for place in missing_docstrings(path)]
    assert not missing, "missing docstrings:\n" + "\n".join(missing)
