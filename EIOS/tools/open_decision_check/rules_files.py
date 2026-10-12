"""Rule kinds that look at what a repository declares rather than at line text.

* ``manifest_dependency`` - ``names``: dependency names (``*`` globs allowed) that must not appear
  in a package manifest or lockfile. Optional ``include`` overrides the manifest globs.
* ``file_pattern`` - ``patterns``: path globs; the existence of a matching file is the finding.
* ``route_definition`` - ``decorators``: attribute names (``get``, ``post``...) whose decorator
  form ``@<obj>.<name>("/path")`` registers an HTTP route; optional ``registrations``: call names
  (``add_api_route``...) taking a ``"/path"`` first argument. Python files only.

Which paths are exempt is the decision's ``allowed_paths``, handled by the engine.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator, Sequence

from tools.open_decision_check.config import RuleSpec
from tools.open_decision_check.manifests import (
    ManifestError,
    dependency_names,
    names_matching,
)
from tools.open_decision_check.rules_base import (
    CompiledRule,
    Hit,
    SourceFile,
    compiled,
    path_matches,
    string_list,
)

MANIFEST_GLOBS = (
    "**/package.json",
    "**/package-lock.json",
    "**/pyproject.toml",
    "**/requirements*.txt",
    "**/uv.lock",
    "**/poetry.lock",
    "**/yarn.lock",
    "**/pnpm-lock.yaml",
)
_PY_GLOBS = ("**/*.py",)


# --- manifest_dependency -------------------------------------------------------------------


def _manifest_hits(source: SourceFile, patterns: Sequence[str]) -> Iterator[Hit]:
    try:
        declared = dependency_names(source.path, source.text)
    except ManifestError as exc:
        yield Hit(source.path, 1, f"{exc}, so a forbidden dependency cannot be ruled out")
        return
    for name, line in names_matching(declared, patterns):
        yield Hit(source.path, line, f"declares dependency {name!r}, which this rule forbids")


def build_manifest_dependency(spec: RuleSpec) -> CompiledRule:
    patterns = string_list(spec, "names")
    globs = string_list(spec, "include", default=MANIFEST_GLOBS)

    def check(files: Sequence[SourceFile]) -> tuple[Hit, ...]:
        selected = (f for f in files if path_matches(f.path, globs))
        return tuple(h for f in selected for h in _manifest_hits(f, patterns))

    return compiled(spec, check, MANIFEST_GLOBS)


# --- file_pattern --------------------------------------------------------------------------


def build_file_pattern(spec: RuleSpec) -> CompiledRule:
    patterns = string_list(spec, "patterns")

    def check(files: Sequence[SourceFile]) -> tuple[Hit, ...]:
        message = "file matches a path pattern this rule forbids"
        return tuple(Hit(f.path, 1, message) for f in files if path_matches(f.path, patterns))

    return CompiledRule(check, include=patterns, exclude=string_list(spec, "exclude", default=()))


# --- route_definition ----------------------------------------------------------------------


def _route_path(call: ast.Call) -> str | None:
    """The string route a call registers (first positional or ``path``/``rule`` keyword)."""
    candidates = [*call.args[:1], *(k.value for k in call.keywords if k.arg in ("path", "rule"))]
    for node in candidates:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith("/"):
                return node.value
    return None


def _call_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else None


def _route_hits(
    source: SourceFile, decorators: frozenset[str], calls: frozenset[str]
) -> Iterator[Hit]:
    try:
        tree = ast.parse(source.text, filename=source.path)
    except SyntaxError as exc:
        message = "file cannot be parsed, so a forbidden route cannot be ruled out"
        yield Hit(source.path, exc.lineno or 1, message)
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            for decorator in node.decorator_list:
                found = _decorator_route(decorator, decorators)
                if found:
                    yield Hit(source.path, decorator.lineno, f"registers route {found!r}")
        elif isinstance(node, ast.Call) and _call_name(node) in calls:
            route = _route_path(node)
            if route:
                yield Hit(source.path, node.lineno, f"registers route {route!r}")


def _decorator_route(decorator: ast.expr, names: frozenset[str]) -> str | None:
    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
        if decorator.func.attr in names:
            return _route_path(decorator)
    return None


def build_route_definition(spec: RuleSpec) -> CompiledRule:
    decorators = frozenset(string_list(spec, "decorators"))
    calls = frozenset(string_list(spec, "registrations", default=()))

    def check(files: Sequence[SourceFile]) -> tuple[Hit, ...]:
        python = (f for f in files if f.path.endswith(".py"))
        return tuple(dict.fromkeys(h for f in python for h in _route_hits(f, decorators, calls)))

    return compiled(spec, check, _PY_GLOBS)
