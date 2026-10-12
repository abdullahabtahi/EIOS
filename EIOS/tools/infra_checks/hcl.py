"""Static HCL loading for the infra checks.

Terraform is read with python-hcl2 (no terraform binary, no network, no provider download), so
the checks run in unit tests and in the quick CI stage. The parsed form keeps hcl2's value
conventions: a quoted string literal is ``'"text"'`` (no interpolation inside), a reference or
expression is ``'${...}'``, numbers and booleans are native, lists and objects nest.

Line numbers are not part of hcl2's output; they are recovered from the source text.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hcl2

from tools.common.findings import Finding
from tools.repo_checks._walk import iter_files, relative_posix

INFRA_DIR = "infra"
ENV_PARENT = "infra/envs"
MODULE_PARENT = "infra/modules"
RULE_PARSE = "infra.hcl.parse"
_META_KEY = re.compile(r"^__\w+__$")
_REF = re.compile(r"^\$\{(.*)\}$", re.DOTALL)
_LOCAL_REF = re.compile(r"^local\.(\w+)$")
_VAR_REF = re.compile(r"^var\.(\w+)$")
_MAX_RESOLVE_DEPTH = 5
_PLACEHOLDER_PREFIXES = ("placeholder", "replace", "example", "<")


@dataclass(frozen=True, slots=True)
class Block:
    """One top-level Terraform block: ``kind "label" ...`` with its parsed body."""

    kind: str
    labels: tuple[str, ...]
    body: Mapping[str, Any]
    file: str
    line: int

    @property
    def name(self) -> str:
        return self.labels[-1] if self.labels else ""

    def get(self, key: str) -> Any:
        return self.body.get(key)


@dataclass(frozen=True, slots=True)
class Unit:
    """All ``*.tf`` files of one directory, read as a single Terraform module."""

    name: str
    directory: str
    blocks: tuple[Block, ...]

    def of_kind(self, kind: str) -> tuple[Block, ...]:
        return tuple(b for b in self.blocks if b.kind == kind)

    def resources(self, type_name: str) -> tuple[Block, ...]:
        return tuple(b for b in self.of_kind("resource") if b.labels[:1] == (type_name,))

    def module_calls(self, module_name: str) -> tuple[Block, ...]:
        """Module blocks whose ``source`` ends in ``/<module_name>``."""
        return tuple(b for b in self.of_kind("module") if source_name(b) == module_name)

    def variable(self, name: str) -> Block | None:
        return next((b for b in self.of_kind("variable") if b.name == name), None)

    def local_values(self) -> Mapping[str, Any]:
        merged: dict[str, Any] = {}
        for block in self.of_kind("locals"):
            merged.update(block.body)
        return merged


@dataclass(frozen=True, slots=True)
class InfraTree:
    """Every Terraform directory under ``infra/``, plus where each file's lines are."""

    units: Mapping[str, Unit]
    sources: Mapping[str, tuple[str, ...]]
    parse_findings: tuple[Finding, ...]

    @property
    def envs(self) -> Mapping[str, Unit]:
        return _children(self.units, ENV_PARENT)

    @property
    def modules(self) -> Mapping[str, Unit]:
        return _children(self.units, MODULE_PARENT)

    def attr_line(self, block: Block, attr: str) -> int:
        """Line of ``attr`` inside ``block`` (the block's own line when it is not found)."""
        lines = self.sources.get(block.file, ())
        pattern = re.compile(rf"^\s*{re.escape(attr)}\s*=")
        for index in range(block.line - 1, len(lines)):
            if pattern.match(lines[index]):
                return index + 1
        return block.line


def _children(units: Mapping[str, Unit], parent: str) -> Mapping[str, Unit]:
    return {u.name: u for u in units.values() if u.directory.rsplit("/", 1)[0] == parent}


def source_name(block: Block) -> str:
    """Last path segment of a module block's literal ``source`` ('' when it is not literal)."""
    source = literal_str(block.get("source"))
    return source.rstrip("/").rsplit("/", 1)[-1] if source else ""


# --- value helpers ------------------------------------------------------------------------------


def literal_str(value: Any) -> str | None:
    """The text of a quoted literal without interpolation; ``None`` for anything else."""
    if isinstance(value, str) and len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        inner = value[1:-1]
        return None if "${" in inner else inner
    return None


def ref_of(value: Any) -> str | None:
    """The expression inside ``${...}``; ``None`` for a literal."""
    if isinstance(value, str):
        match = _REF.match(value)
        return match.group(1).strip() if match else None
    return None


def number_of(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return value


def literal_list(value: Any) -> list[str] | None:
    """A list made only of quoted literals; ``None`` otherwise."""
    if not isinstance(value, list):
        return None
    items = [literal_str(item) for item in value]
    return None if any(item is None for item in items) else [i for i in items if i is not None]


def is_placeholder(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered == "" or lowered.startswith(_PLACEHOLDER_PREFIXES) or "replace_me" in lowered


def walk_literals(value: Any, key: str = "") -> Iterator[tuple[str, str]]:
    """Every quoted literal in ``value`` with the attribute name that holds it."""
    text = literal_str(value)
    if text is not None:
        yield key, text
    elif isinstance(value, Mapping):
        for child_key, child in value.items():
            yield from walk_literals(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from walk_literals(child, key)


def resolve(unit: Unit, value: Any, depth: int = 0) -> Any:
    """Follow ``local.x`` and ``var.x`` (its default) to a value; unresolvable stays as is."""
    expression = ref_of(value)
    if expression is None or depth >= _MAX_RESOLVE_DEPTH:
        return value
    local = _LOCAL_REF.match(expression)
    if local and local.group(1) in unit.local_values():
        return resolve(unit, unit.local_values()[local.group(1)], depth + 1)
    var = _VAR_REF.match(expression)
    declared = unit.variable(var.group(1)) if var else None
    if declared is not None and "default" in declared.body:
        return resolve(unit, declared.body["default"], depth + 1)
    return value


# --- parsing ------------------------------------------------------------------------------------


def _clean(value: Any) -> Any:
    """Copy of ``value`` without hcl2 bookkeeping keys, with quotes removed from keys."""
    if isinstance(value, dict):
        return {
            _unquote(str(k)): _clean(v) for k, v in value.items() if not _META_KEY.match(str(k))
        }
    if isinstance(value, list):
        return [_clean(item) for item in value]
    return value


def _unquote(key: str) -> str:
    return key[1:-1] if len(key) >= 2 and key[0] == key[-1] == '"' else key


def _labelled(kind: str, item: Mapping[str, Any]) -> Iterator[tuple[tuple[str, ...], Any]]:
    """Yield ``(labels, body)`` for one hcl2 item of a block kind."""
    if kind in ("module", "variable", "output", "provider"):
        for label, body in item.items():
            yield (_unquote(label),), body
    elif kind in ("resource", "data"):
        for type_name, named in item.items():
            for label, body in named.items():
                yield (_unquote(type_name), _unquote(label)), body
    else:
        yield (), item


def _block_line(lines: tuple[str, ...], kind: str, labels: tuple[str, ...], start: int) -> int:
    quoted = "".join(rf'\s+"{re.escape(label)}"' for label in labels)
    pattern = re.compile(rf"^\s*{re.escape(kind)}{quoted}\s*\{{")
    for index in range(start, len(lines)):
        if pattern.match(lines[index]):
            return index + 1
    return 0


def _blocks_of(path: str, text: str, data: Mapping[str, Any]) -> tuple[Block, ...]:
    lines = tuple(text.splitlines())
    cursor: dict[tuple[str, tuple[str, ...]], int] = {}
    blocks: list[Block] = []
    for kind, items in data.items():
        for item in items:
            for labels, body in _labelled(kind, item):
                line = _block_line(lines, kind, labels, cursor.get((kind, labels), 0))
                cursor = {**cursor, (kind, labels): line}
                blocks.append(Block(kind, labels, _clean(body), path, max(line, 1)))
    return tuple(blocks)


def parse_text(path: str, text: str) -> tuple[Block, ...]:
    """Parse one Terraform file; raises ``ValueError`` with the line on a syntax error."""
    try:
        data = hcl2.loads(text)
    except Exception as exc:  # noqa: BLE001 - hcl2/lark raise several unrelated exception types
        line = getattr(exc, "line", None)
        where = f" at line {line}" if isinstance(line, int) else ""
        raise ValueError(f"cannot parse Terraform{where}: {type(exc).__name__}") from exc
    return _blocks_of(path, text, data)


def parse_attributes(text: str) -> dict[str, Any]:
    """Parse an attribute-only file such as ``*.tfvars``; raises ``ValueError`` on bad syntax."""
    try:
        return dict(_clean(hcl2.loads(text)))
    except Exception as exc:  # noqa: BLE001 - see parse_text
        raise ValueError(f"cannot parse attributes: {type(exc).__name__}") from exc


def _tf_directories(root: Path) -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = {}
    for file in iter_files(root, start=INFRA_DIR, suffixes=frozenset({".tf"})):
        directory = relative_posix(root, file.parent)
        grouped[directory] = [*grouped.get(directory, []), file]
    return grouped


def load_infra(repo_root: Path) -> InfraTree:
    """Parse every ``*.tf`` file under ``infra/``; syntax errors become findings, not crashes."""
    root = repo_root.resolve()
    units: dict[str, Unit] = {}
    sources: dict[str, tuple[str, ...]] = {}
    problems: list[Finding] = []
    for directory, files in _tf_directories(root).items():
        blocks: list[Block] = []
        for file in files:
            relative = relative_posix(root, file)
            text = file.read_text(encoding="utf-8", errors="replace")
            sources = {**sources, relative: tuple(text.splitlines())}
            try:
                blocks.extend(parse_text(relative, text))
            except ValueError as exc:
                problems.append(Finding(relative, 1, RULE_PARSE, str(exc)))
        units[directory] = Unit(directory.rsplit("/", 1)[-1], directory, tuple(blocks))
    return InfraTree(units, sources, tuple(problems))
