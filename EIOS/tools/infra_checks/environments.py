"""Environment entity rules: known names, own project and state prefix, no cross-references.

Rule ids: ``infra.env.unknown``, ``infra.env.missing``, ``infra.env.no_project_ref``,
``infra.env.no_state_prefix``, ``infra.env.shared_project``, ``infra.env.shared_state_prefix``,
``infra.env.shared_literal``, ``infra.env.cross_reference``, ``infra.env.approval_required``.

Findings about a whole environment name the environment directory and use line 0.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from tools.common.findings import Finding
from tools.infra_checks.hcl import (
    InfraTree,
    Unit,
    is_placeholder,
    literal_str,
    walk_literals,
)

ENVIRONMENT_NAMES = ("dev", "stage", "prod-like")
APPROVAL_REQUIRED = frozenset({"prod-like"})
PROJECT_VARIABLE = "project_id"
ENV_PARENT = "infra/envs"
_SHARED_KEYS = frozenset(
    {
        "bucket",
        "bucket_name",
        "project",
        "project_id",
        "credentials",
        "key_ring",
        "state_bucket",
        "service_account",
        "service_account_email",
    }
)


@dataclass(frozen=True, slots=True)
class Environment:
    """One deployment environment as declared by its Terraform root."""

    name: str
    directory: str
    project_ref: str | None
    state_prefix: str | None
    approval_required: bool


def _backend_prefix(unit: Unit) -> str | None:
    for block in unit.of_kind("terraform"):
        for backend in block.get("backend") or ():
            for body in backend.values() if isinstance(backend, dict) else ():
                prefix = literal_str(body.get("prefix")) if isinstance(body, dict) else None
                if prefix:
                    return prefix
    return None


def _project_ref(unit: Unit) -> str | None:
    variable = unit.variable(PROJECT_VARIABLE)
    if variable is None:
        return None
    default = literal_str(variable.get("default"))
    return default if default is not None else f"var.{PROJECT_VARIABLE}"


def _literal_project(environment: Environment) -> str | None:
    ref = environment.project_ref
    return ref if ref is not None and not ref.startswith("var.") else None


def describe_environments(tree: InfraTree) -> tuple[Environment, ...]:
    """One ``Environment`` per directory under ``infra/envs``, sorted by name."""
    return tuple(
        Environment(
            name=name,
            directory=unit.directory,
            project_ref=_project_ref(unit),
            state_prefix=_backend_prefix(unit),
            approval_required=name in APPROVAL_REQUIRED,
        )
        for name, unit in sorted(tree.envs.items())
    )


def _finding(directory: str, rule: str, message: str) -> Finding:
    return Finding(directory, 0, rule, message)


def _names(tree: InfraTree) -> Iterator[Finding]:
    for name, unit in sorted(tree.envs.items()):
        if name not in ENVIRONMENT_NAMES:
            allowed = ", ".join(ENVIRONMENT_NAMES)
            yield _finding(unit.directory, "infra.env.unknown", f"'{name}' is not one of {allowed}")
    for name in ENVIRONMENT_NAMES:
        if name not in tree.envs:
            yield _finding(ENV_PARENT, "infra.env.missing", f"environment '{name}' has no root")


def _declared(tree: InfraTree, environments: Sequence[Environment]) -> Iterator[Finding]:
    for env in environments:
        if env.project_ref is None:
            msg = f"declares no variable '{PROJECT_VARIABLE}'; each environment owns its project"
            yield _finding(env.directory, "infra.env.no_project_ref", msg)
        if env.state_prefix is None:
            msg = "has no gcs backend with a literal state prefix"
            yield _finding(env.directory, "infra.env.no_state_prefix", msg)
        yield from _approval(tree.envs[env.name], env)


def _approval(unit: Unit, env: Environment) -> Iterator[Finding]:
    declared = unit.local_values().get("approval_required")
    if isinstance(declared, bool) and declared != env.approval_required:
        msg = f"approval_required = {str(declared).lower()} contradicts policy for '{env.name}'"
        yield _finding(env.directory, "infra.env.approval_required", msg)


def _shared(
    environments: Sequence[Environment], rule: str, label: str, values: dict[str, str | None]
) -> Iterator[Finding]:
    groups: dict[str, list[Environment]] = defaultdict(list)
    for env in environments:
        value = values[env.name]
        if value:
            groups[value].append(env)
    for value, members in sorted(groups.items()):
        if len(members) > 1:
            names = ", ".join(m.name for m in members)
            for member in members:
                yield _finding(member.directory, rule, f"{label} '{value}' is shared by {names}")


def _isolation(environments: Sequence[Environment]) -> Iterator[Finding]:
    projects = {e.name: _literal_project(e) for e in environments}
    prefixes = {e.name: e.state_prefix for e in environments}
    yield from _shared(environments, "infra.env.shared_project", "project", projects)
    yield from _shared(environments, "infra.env.shared_state_prefix", "state prefix", prefixes)


def _own_values(env: Environment) -> frozenset[str]:
    return frozenset(v for v in (_literal_project(env), env.state_prefix) if v)


def _foreign_hits(
    unit: Unit, env: Environment, others: Sequence[Environment]
) -> Iterator[tuple[str, str]]:
    own = _own_values(env)
    other_names = {o.name for o in others if o.name != env.name}
    for block in unit.blocks:
        for _key, text in walk_literals(dict(block.body)):
            if text in own:
                continue
            for other in others:
                if other.name != env.name and _mentions(text, other):
                    yield block.file, other.name
        yield from _source_hits(block.file, block.get("source"), other_names)


def _mentions(text: str, other: Environment) -> bool:
    project = _literal_project(other)
    if project and text == project:
        return True
    return re.search(rf"envs/{re.escape(other.name)}(?![\w-])", text) is not None


def _source_hits(file: str, source: object, other_names: set[str]) -> Iterator[tuple[str, str]]:
    text = literal_str(source)
    if text is None:
        return
    for segment in text.split("/"):
        if segment in other_names:
            yield file, segment


def _cross_references(tree: InfraTree, environments: Sequence[Environment]) -> Iterator[Finding]:
    for env in environments:
        seen: set[str] = set()
        for _file, other in _foreign_hits(tree.envs[env.name], env, environments):
            if other not in seen:
                seen.add(other)
                msg = f"refers to environment '{other}' (project, state prefix or module path)"
                yield _finding(env.directory, "infra.env.cross_reference", msg)


def _shared_literals(tree: InfraTree, environments: Sequence[Environment]) -> Iterator[Finding]:
    owners: dict[tuple[str, str], list[Environment]] = defaultdict(list)
    for env in environments:
        for block in tree.envs[env.name].blocks:
            if block.kind == "terraform":
                continue
            for key, text in walk_literals(dict(block.body)):
                if key in _SHARED_KEYS and not is_placeholder(text):
                    owners[(key, text)].append(env)
    reported: set[tuple[str, str, str]] = set()
    for (key, text), members in sorted(owners.items()):
        names = sorted({m.name for m in members})
        if len(names) < 2:
            continue
        for member in members:
            token = (member.name, key, text)
            if token not in reported:
                reported.add(token)
                others = ", ".join(n for n in names if n != member.name)
                msg = f"{key} '{text}' is also used by {others}"
                yield _finding(member.directory, "infra.env.shared_literal", msg)


def check_environments(tree: InfraTree) -> tuple[Finding, ...]:
    """All environment rules over a parsed ``infra/`` tree."""
    environments = describe_environments(tree)
    return (
        *_names(tree),
        *_declared(tree, environments),
        *_isolation(environments),
        *_cross_references(tree, environments),
        *_shared_literals(tree, environments),
    )
