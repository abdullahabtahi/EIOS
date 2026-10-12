"""Dependency names declared in package manifests and lockfiles, with the line they appear on.

Formats are chosen by file name: ``package.json``, ``package-lock.json``, ``pyproject.toml``,
``requirements*.txt``, ``uv.lock``, ``poetry.lock``, ``yarn.lock`` and ``pnpm-lock.yaml``. A file
that cannot be parsed raises ``ManifestError`` so the caller fails closed.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Iterator, Mapping, Sequence
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

NPM_SECTIONS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
_YARN_KEY = re.compile(r"""^["']?(@?[^@\s"',:]+)@""")
_PNPM_KEY = re.compile(r"""^\s{2,6}["'/]*(@?[^@\s"',:/]+(?:/[^@\s"',:/]+)?)@""")

type Names = tuple[tuple[str, int], ...]


class ManifestError(ValueError):
    """The manifest cannot be read, so a banned dependency cannot be ruled out."""


def normalize(name: str) -> str:
    """Comparable form of a package name (case and ``-``/``_``/``.`` runs folded)."""
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def _line_of(text: str, needle: str) -> int:
    index = text.find(needle)
    return text.count("\n", 0, index) + 1 if index >= 0 else 1


def _npm_section(entries: Mapping[str, object], text: str) -> Iterator[tuple[str, int]]:
    for name, value in entries.items():
        yield str(name), _line_of(text, f'"{name}"')
        nested = value.get("dependencies") if isinstance(value, Mapping) else None
        if isinstance(nested, Mapping):  # lockfile v1 nests transitive dependencies
            yield from _npm_section(nested, text)


def _npm_names(data: object, text: str) -> Iterator[tuple[str, int]]:
    if not isinstance(data, Mapping):
        raise ManifestError("top-level JSON value is not an object")
    for section in NPM_SECTIONS:
        entries = data.get(section)
        if isinstance(entries, Mapping):
            yield from _npm_section(entries, text)
    packages = data.get("packages")
    if isinstance(packages, Mapping):
        for key in packages:
            name = str(key).rsplit("node_modules/", 1)[-1]
            if name:
                yield name, _line_of(text, f'"{key}"')


def _requirement(spec: object) -> str | None:
    match = _REQUIREMENT_NAME.match(spec) if isinstance(spec, str) else None
    return match.group(1) if match else None


def _toml_requirements(data: Mapping[str, object]) -> Iterator[str]:
    project = data.get("project", {})
    tool = data.get("tool", {})
    groups: list[object] = [data.get("dependency-groups", {}), data.get("build-system", {})]
    if isinstance(project, Mapping):
        groups.append(project.get("optional-dependencies", {}))
        groups.append({"project": project.get("dependencies", [])})
    if isinstance(tool, Mapping):
        uv = tool.get("uv", {})
        groups.append({"uv": uv.get("dev-dependencies", [])} if isinstance(uv, Mapping) else {})
        poetry = tool.get("poetry", {})
        if isinstance(poetry, Mapping):
            groups.append({"poetry": list(poetry.get("dependencies", {}))})
            groups.append({"poetry": list(poetry.get("dev-dependencies", {}))})
    for group in groups:
        for value in group.values() if isinstance(group, Mapping) else ():
            yield from (v for v in _flatten(value) if isinstance(v, str))


def _flatten(value: object) -> Iterator[object]:
    if isinstance(value, list):
        for item in value:
            yield from _flatten(item)
    else:
        yield value


def _pyproject_names(text: str) -> Iterator[tuple[str, int]]:
    for spec in _toml_requirements(tomllib.loads(text)):
        name = _requirement(spec)
        if name:
            yield name, _line_of(text, spec)


def _lock_names(text: str) -> Iterator[tuple[str, int]]:
    data = tomllib.loads(text)
    for package in data.get("package", []):
        name = package.get("name") if isinstance(package, Mapping) else None
        if isinstance(name, str):
            yield name, _line_of(text, f'name = "{name}"')


def _requirements_names(text: str) -> Iterator[tuple[str, int]]:
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split(" #", 1)[0].strip()
        if line and not line.startswith(("#", "-")):
            name = _requirement(line)
            if name:
                yield name, number


def _regex_names(text: str, pattern: re.Pattern[str]) -> Iterator[tuple[str, int]]:
    for number, line in enumerate(text.splitlines(), start=1):
        match = pattern.match(line)
        if match:
            yield match.group(1), number


def dependency_names(filename: str, text: str) -> Names:
    """Every ``(name, line)`` the manifest ``filename`` declares; ``ManifestError`` on failure."""
    base = PurePosixPath(filename).name
    try:
        if base in ("package.json", "package-lock.json"):
            return tuple(_npm_names(json.loads(text), text))
        if base == "pyproject.toml":
            return tuple(_pyproject_names(text))
        if base in ("uv.lock", "poetry.lock"):
            return tuple(_lock_names(text))
        if base.startswith("requirements") and base.endswith(".txt"):
            return tuple(_requirements_names(text))
        if base == "yarn.lock":
            return tuple(_regex_names(text, _YARN_KEY))
        if base == "pnpm-lock.yaml":
            return tuple(_regex_names(text, _PNPM_KEY))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ManifestError(f"cannot parse {base}: {exc}") from exc
    raise ManifestError(f"unsupported manifest format: {base}")


def names_matching(names: Sequence[tuple[str, int]], patterns: Sequence[str]) -> Names:
    """The ``(name, line)`` pairs whose normalized name matches any normalized glob."""
    wanted = [normalize(p) for p in patterns]
    return tuple(
        (name, line)
        for name, line in names
        if any(fnmatchcase(normalize(name), pattern) for pattern in wanted)
    )
