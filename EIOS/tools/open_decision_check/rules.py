"""Rule kinds for the open-decision engine.

A rule kind turns a ``RuleSpec`` (parameters from config) into a checker that scans source
files and returns hits. New kinds are added to ``RULE_KINDS``; decisions use them from config.

* ``import_root`` - ``modules``: Python import roots that must not be imported.
* ``bound_value`` - ``patterns``: regular expressions that must not appear in any scanned line.

The file, route and prose kinds live in ``rules_files.py`` and ``rules_text.py``; this module
is the single registry (``RULE_KINDS``) and entry point (``build_rule``).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from types import MappingProxyType

from eios.common.errors import ConfigError
from tools.open_decision_check.config import CONFIG_PATH, RuleSpec
from tools.open_decision_check.rules_base import (
    Checker,
    CompiledRule,
    Hit,
    SourceFile,
    compiled,
    string_list,
)
from tools.open_decision_check.rules_files import (
    build_file_pattern,
    build_manifest_dependency,
    build_route_definition,
)
from tools.open_decision_check.rules_text import build_spec_text

__all__ = ["RULE_KINDS", "Checker", "CompiledRule", "Hit", "SourceFile", "build_rule"]

_MODULE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
_DYNAMIC_IMPORTERS = frozenset({"import_module", "__import__"})


# --- import_root ---------------------------------------------------------------------------


def _import_candidates(node: ast.AST) -> tuple[str, ...]:
    """Dotted names an import statement or dynamic-import call refers to."""
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return (node.module, *(f"{node.module}.{alias.name}" for alias in node.names))
    if isinstance(node, ast.Call) and node.args:
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        first = node.args[0]
        if name in _DYNAMIC_IMPORTERS and isinstance(first, ast.Constant):
            return (first.value,) if isinstance(first.value, str) else ()
    return ()


def _banned_root(candidates: Sequence[str], roots: Sequence[str]) -> str | None:
    for name in candidates:
        for root in roots:
            if name == root or name.startswith(root + "."):
                return root
    return None


def _import_hits(source: SourceFile, roots: Sequence[str]) -> Iterator[Hit]:
    try:
        tree = ast.parse(source.text, filename=source.path)
    except SyntaxError as exc:
        message = "file cannot be parsed, so a banned import cannot be ruled out"
        yield Hit(source.path, exc.lineno or 1, message)
        return
    for node in ast.walk(tree):
        banned = _banned_root(_import_candidates(node), roots)
        if banned is not None:
            line = getattr(node, "lineno", 1)
            yield Hit(source.path, line, f"imports {banned!r}, a module this rule forbids")


def _build_import_root(spec: RuleSpec) -> CompiledRule:
    roots = string_list(spec, "modules")
    for position, root in enumerate(roots):
        if not _MODULE_NAME.match(root):
            where = f"{spec.where}.modules[{position}]"
            raise ConfigError(CONFIG_PATH, where, f"not a dotted Python module name: {root!r}")

    def check(files: Sequence[SourceFile]) -> tuple[Hit, ...]:
        hits = (h for f in files if f.path.endswith(".py") for h in _import_hits(f, roots))
        return tuple(hits)

    return compiled(spec, check)


# --- bound_value ---------------------------------------------------------------------------


def _build_bound_value(spec: RuleSpec) -> CompiledRule:
    patterns: list[re.Pattern[str]] = []
    for position, text in enumerate(string_list(spec, "patterns")):
        try:
            patterns.append(re.compile(text))
        except re.error as exc:
            where = f"{spec.where}.patterns[{position}]"
            raise ConfigError(CONFIG_PATH, where, f"invalid regular expression: {exc}") from exc

    def check(files: Sequence[SourceFile]) -> tuple[Hit, ...]:
        hits: list[Hit] = []
        for source in files:
            for number, line in enumerate(source.text.splitlines(), start=1):
                for position, pattern in enumerate(patterns):
                    if pattern.search(line):
                        message = f"matches patterns[{position}] of a rule this decision forbids"
                        hits.append(Hit(source.path, number, message))
        return tuple(hits)

    return compiled(spec, check)


type CheckerBuilder = Callable[[RuleSpec], CompiledRule]

RULE_KINDS: Mapping[str, CheckerBuilder] = MappingProxyType(
    {
        "import_root": _build_import_root,
        "bound_value": _build_bound_value,
        "manifest_dependency": build_manifest_dependency,
        "file_pattern": build_file_pattern,
        "route_definition": build_route_definition,
        "spec_text": build_spec_text,
    }
)


def build_rule(spec: RuleSpec) -> CompiledRule:
    """The compiled rule for ``spec``; ``ConfigError`` for an unknown kind or bad parameters."""
    builder = RULE_KINDS.get(spec.kind)
    if builder is None:
        known = ", ".join(sorted(RULE_KINDS))
        message = f"unknown kind {spec.kind!r}; known: {known}"
        raise ConfigError(CONFIG_PATH, f"{spec.where}.kind", message)
    return builder(spec)
