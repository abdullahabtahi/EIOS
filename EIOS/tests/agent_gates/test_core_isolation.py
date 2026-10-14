"""The judge core must stay standard-library only and parse as Python 3.12 (spec 022, research R-1)."""

import ast
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[2] / "src" / "eios" / "agent_gates" / "core"
FILES = sorted(CORE.glob("*.py"))


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("path", FILES, ids=[f.name for f in FILES])
def test_core_module_uses_only_the_standard_library(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 12))
    foreign = _imported_roots(tree) - set(sys.stdlib_module_names) - {"__future__"}
    assert not foreign, f"{path.name} imports non-standard modules: {sorted(foreign)}"


def test_core_directory_exists() -> None:
    assert CORE.is_dir()
