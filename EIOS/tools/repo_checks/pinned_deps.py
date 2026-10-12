"""Fail when ``uv.lock`` is missing or out of sync with ``pyproject.toml``.

Pure Python, no network, no ``uv``: compares the root project's direct dependency names.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from eios.common.errors import ConfigError
from tools.common.findings import Finding

RULE_ID = "repo.pinned_deps"
PYPROJECT = "pyproject.toml"
LOCKFILE = "uv.lock"

_NAME = re.compile(r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)")


def _normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _load_toml(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(path.name, "$", f"cannot read TOML: {exc}") from exc


def _requirement_name(spec: str, where: str) -> str:
    match = _NAME.match(spec)
    if match is None:
        raise ConfigError(PYPROJECT, where, f"cannot read a dependency name from {spec!r}")
    return _normalise(match.group(1))


def _as_list(value: object, file: str, where: str) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(file, where, "expected a list")
    return value


def _as_table(value: object, file: str, where: str) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(file, where, "expected a table")
    return value


def _table_specs(table: dict[str, object], where: str) -> list[tuple[object, str]]:
    """Every requirement of a table of named requirement lists (dependency groups, extras)."""
    specs: list[tuple[object, str]] = []
    for key, items in table.items():
        label = f"{where}.{key}"
        specs.extend((s, label) for s in _as_list(items, PYPROJECT, label))
    return specs


def _declared(pyproject: dict[str, object]) -> tuple[str, frozenset[str]]:
    project = _as_table(pyproject.get("project"), PYPROJECT, "project")
    name = project.get("name")
    if not isinstance(name, str) or not name:
        raise ConfigError(PYPROJECT, "project.name", "a project name is required")
    specs = [
        (s, "project.dependencies")
        for s in _as_list(project.get("dependencies"), PYPROJECT, "project.dependencies")
    ]
    groups = _as_table(pyproject.get("dependency-groups"), PYPROJECT, "dependency-groups")
    extras = _as_table(
        project.get("optional-dependencies"), PYPROJECT, "project.optional-dependencies"
    )
    specs.extend(_table_specs(groups, "dependency-groups"))
    specs.extend(_table_specs(extras, "project.optional-dependencies"))
    names = {_requirement_name(s, where) for s, where in specs if isinstance(s, str)}
    return _normalise(name), frozenset(names)


def _entry_names(entries: object, where: str) -> set[str]:
    names: set[str] = set()
    for entry in _as_list(entries, LOCKFILE, where):
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise ConfigError(LOCKFILE, where, "each requirement must be a table with a name")
        names.add(_normalise(entry["name"]))
    return names


def _root_package(lock: dict[str, object], project: str) -> dict[str, object] | None:
    for package in _as_list(lock.get("package"), LOCKFILE, "package"):
        if isinstance(package, dict) and _normalise(str(package.get("name", ""))) == project:
            return package
    return None


def _locked(package: dict[str, object]) -> frozenset[str]:
    metadata = _as_table(package.get("metadata"), LOCKFILE, "package.metadata")
    names = _entry_names(metadata.get("requires-dist"), "package.metadata.requires-dist")
    dev = _as_table(metadata.get("requires-dev"), LOCKFILE, "package.metadata.requires-dev")
    for group, entries in dev.items():
        names |= _entry_names(entries, f"package.metadata.requires-dev.{group}")
    return frozenset(names)


def _finding(message: str) -> tuple[Finding, ...]:
    return (Finding(LOCKFILE, 1, RULE_ID, message),)


def check_pinned_deps(repo_root: Path) -> tuple[Finding, ...]:
    """Return findings when the lockfile is absent or disagrees with ``pyproject.toml``."""
    root = repo_root.resolve()
    if not (root / PYPROJECT).is_file():
        return ()
    project, declared = _declared(_load_toml(root / PYPROJECT))
    if not (root / LOCKFILE).is_file():
        return _finding("uv.lock is missing; run `uv lock` and commit it")
    package = _root_package(_load_toml(root / LOCKFILE), project)
    if package is None:
        return _finding(f"uv.lock has no entry for the root project {project!r}; run `uv lock`")
    locked = _locked(package)
    problems = []
    if declared - locked:
        problems.append("declared but not locked: " + ", ".join(sorted(declared - locked)))
    if locked - declared:
        problems.append("locked but not declared: " + ", ".join(sorted(locked - declared)))
    if not problems:
        return ()
    return _finding("uv.lock is out of sync with pyproject.toml (" + "; ".join(problems) + ")")
