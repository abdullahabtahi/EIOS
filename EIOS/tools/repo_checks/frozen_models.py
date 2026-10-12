"""Flag non-frozen Pydantic models and dataclasses under ``src/eios`` (``ast`` based).

Rules: a direct ``BaseModel`` subclass must set ``frozen=True`` (class keyword or
``model_config``); a ``StrictModel`` subclass is frozen unless it sets ``frozen=False``; a
``@dataclass`` must pass ``frozen=True``.
"""

from __future__ import annotations

import ast
from collections.abc import Sequence
from pathlib import Path

from eios.common.errors import ConfigError
from tools.common.findings import Finding
from tools.repo_checks._walk import iter_files, relative_posix

RULE_ID = "repo.frozen_model"
SOURCE_TREE = "src/eios"

_UNSET = object()


def _name(node: ast.expr) -> str | None:
    """The trailing identifier of ``Name`` / ``a.b.Name`` / ``Call`` targets."""
    if isinstance(node, ast.Call):
        return _name(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    return node.id if isinstance(node, ast.Name) else None


def _frozen_value(keywords: Sequence[ast.keyword]) -> object:
    """``True`` / ``False`` for a literal ``frozen=`` keyword, ``None`` if not a literal."""
    for keyword in keywords:
        if keyword.arg == "frozen":
            value = keyword.value
            return value.value if isinstance(value, ast.Constant) else None
    return _UNSET


def _dict_frozen(node: ast.Dict) -> object:
    for key, value in zip(node.keys, node.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == "frozen":
            return value.value if isinstance(value, ast.Constant) else None
    return _UNSET


def _config_frozen(cls: ast.ClassDef) -> object:
    """Frozen setting from the class keyword or a ``model_config`` assignment."""
    from_keyword = _frozen_value(cls.keywords)
    if from_keyword is not _UNSET:
        return from_keyword
    for stmt in cls.body:
        target, value = _assignment(stmt)
        if target != "model_config" or value is None:
            continue
        if isinstance(value, ast.Call):
            return _frozen_value(value.keywords)
        if isinstance(value, ast.Dict):
            return _dict_frozen(value)
        return None
    return _UNSET


def _assignment(stmt: ast.stmt) -> tuple[str | None, ast.expr | None]:
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
        target = stmt.targets[0]
        return (target.id if isinstance(target, ast.Name) else None), stmt.value
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return stmt.target.id, stmt.value
    return None, None


def _model_problem(cls: ast.ClassDef) -> str | None:
    base_names = {_name(base) for base in cls.bases}
    frozen = _config_frozen(cls)
    if frozen is False:
        return "model sets frozen=False"
    if "BaseModel" in base_names and frozen is not True:
        return "BaseModel subclass is not frozen; set frozen=True or derive from StrictModel"
    return None


def _dataclass_problem(cls: ast.ClassDef) -> str | None:
    for decorator in cls.decorator_list:
        if _name(decorator) != "dataclass":
            continue
        keywords = decorator.keywords if isinstance(decorator, ast.Call) else []
        if _frozen_value(keywords) is not True:
            return "dataclass is not frozen; use @dataclass(frozen=True)"
    return None


def _check_tree(file: str, tree: ast.AST) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        problem = _model_problem(node) or _dataclass_problem(node)
        if problem:
            message = f"class {node.name}: {problem}"
            findings.append(Finding(file, node.lineno, RULE_ID, message))
    return findings


def _check_file(root: Path, path: Path) -> list[Finding]:
    relative = relative_posix(root, path)
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(relative, "$", f"cannot read file: {exc}") from exc
    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError as exc:
        message = f"cannot parse file for the frozen-model check: {exc.msg}"
        return [Finding(relative, exc.lineno or 1, RULE_ID, message)]
    return _check_tree(relative, tree)


def check_frozen_models(repo_root: Path, *, exclude: Sequence[str] = ()) -> tuple[Finding, ...]:
    """Return a finding per non-frozen model or dataclass under ``src/eios``."""
    root = repo_root.resolve()
    findings: list[Finding] = []
    for path in iter_files(root, start=SOURCE_TREE, suffixes=frozenset({".py"}), exclude=exclude):
        findings.extend(_check_file(root, path))
    return tuple(sorted(findings, key=lambda f: (f.file, f.line)))
