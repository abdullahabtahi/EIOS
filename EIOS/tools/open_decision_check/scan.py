"""Which files the open-decision rules read.

The default scope is ``scan.include`` (suffixes or file names) minus ``scan.exclude``. A rule
with its own ``include`` globs reads exactly those paths (minus its ``exclude``) instead.
``scan.exclude_all`` and ``scan.prototype_paths`` are never walked, for any rule.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from eios.common.errors import ConfigError
from tools.open_decision_check.config import ScanScope
from tools.open_decision_check.rules_base import CompiledRule, SourceFile, path_matches
from tools.repo_checks._walk import is_under, iter_files, relative_posix


def in_default_scope(path: str, scope: ScanScope) -> bool:
    """True when ``path`` is code or configuration text inside the default scan scope."""
    pure = PurePosixPath(path)
    wanted = any(pure.suffix == entry or pure.name == entry for entry in scope.include)
    return wanted and not is_under(path, scope.exclude)


def _read(path: Path, relative: str) -> str:
    """Text of ``path``; empty when it is not UTF-8 (such a file can still match by name)."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""
    except OSError as exc:
        raise ConfigError(relative, "$", f"cannot read file: {exc}") from exc


def read_files(
    repo_root: Path, scope: ScanScope, rules: Sequence[CompiledRule]
) -> tuple[SourceFile, ...]:
    """Every file some rule may need, read once, in sorted path order."""
    globs = [g for rule in rules if rule.include is not None for g in rule.include]
    never = (*scope.exclude_all, *scope.prototype_paths)
    files: list[SourceFile] = []
    for path in iter_files(repo_root, exclude=never):
        relative = relative_posix(repo_root, path)
        if in_default_scope(relative, scope) or path_matches(relative, globs):
            files.append(SourceFile(relative, _read(path, relative)))
    return tuple(files)


def select(
    files: Sequence[SourceFile], scope: ScanScope, rule: CompiledRule
) -> tuple[SourceFile, ...]:
    """The files ``rule`` applies to."""
    if rule.include is None:
        return tuple(f for f in files if in_default_scope(f.path, scope))
    return tuple(
        f
        for f in files
        if path_matches(f.path, rule.include) and not path_matches(f.path, rule.exclude)
    )
