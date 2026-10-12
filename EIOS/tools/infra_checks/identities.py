"""Service Identity rules: one identity per service per environment, explicit least-privilege roles.

``check_identities`` judges ``infra/identities.yaml``; ``check_identity_wiring`` judges the
Terraform that realises it. Rule ids: ``infra.identity.file``, ``.duplicate``, ``.missing``,
``.roles_empty``, ``.role_wildcard``, ``.role_project_wide``, ``.role_invalid``,
``.truth_flag``, ``.truth_reach``, ``.impersonation``, ``.shared``.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eios.common.errors import ConfigError
from tools.common.findings import Finding
from tools.common.yaml_io import load_validated
from tools.infra_checks.environments import ENVIRONMENT_NAMES
from tools.infra_checks.hcl import (
    Block,
    InfraTree,
    Unit,
    literal_list,
    literal_str,
    ref_of,
    resolve,
)

IDENTITIES_PATH = "infra/identities.yaml"
SERVICES = ("skeleton_edge", "skeleton_core", "pipeline", "eval_harness", "release_candidate")
TRUTH_READERS = frozenset({"eval_harness", "pipeline"})
RELEASE_CANDIDATE = "release_candidate"
RC_IMPERSONATION = "workflow=release-candidate.yml"
PROJECT_WIDE_ROLES = frozenset({"roles/editor", "roles/owner", "roles/viewer"})
TRUTH_REACHING_ROLES = frozenset(
    {
        "roles/storage.admin",
        "roles/storage.objectAdmin",
        "roles/storage.objectViewer",
        "roles/storage.legacyBucketReader",
        "roles/storage.legacyBucketOwner",
        "roles/storage.legacyObjectReader",
        "roles/storage.legacyObjectOwner",
    }
)
_ROLE_NAME = re.compile(
    r"^(roles/[A-Za-z0-9_.]+|(projects|organizations)/[^/\s]+/roles/[A-Za-z0-9_.]+)$"
)
_IAM_GRANTS = ("google_project_iam_member", "google_project_iam_binding")

_ROW_SCHEMA: dict[str, object] = {
    "type": "object",
    "required": ["identities"],
    "additionalProperties": False,
    "properties": {
        "identities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "service",
                    "environment",
                    "roles",
                    "can_read_eval_truth",
                    "impersonable_by",
                ],
                "additionalProperties": False,
                "properties": {
                    "service": {"type": "string", "minLength": 1},
                    "environment": {"enum": list(ENVIRONMENT_NAMES)},
                    "roles": {"type": "array", "items": {"type": "string"}},
                    "can_read_eval_truth": {"type": "boolean"},
                    "impersonable_by": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}


@dataclass(frozen=True, slots=True)
class ServiceIdentity:
    """One service's identity in one environment, as declared in ``infra/identities.yaml``."""

    service: str
    environment: str
    roles: tuple[str, ...]
    can_read_eval_truth: bool
    impersonable_by: tuple[str, ...]


def load_identities(repo_root: Path) -> tuple[ServiceIdentity, ...]:
    """Read and validate ``infra/identities.yaml``; raises ``ConfigError`` when it is unusable."""
    data = load_validated(repo_root.resolve() / IDENTITIES_PATH, _ROW_SCHEMA)
    rows: list[Mapping[str, Any]] = data["identities"] if isinstance(data, dict) else []
    return tuple(
        ServiceIdentity(
            service=row["service"],
            environment=row["environment"],
            roles=tuple(row["roles"]),
            can_read_eval_truth=row["can_read_eval_truth"],
            impersonable_by=tuple(row["impersonable_by"]),
        )
        for row in rows
    )


def judge_role(role: str) -> tuple[str, str] | None:
    """``(rule_id, message)`` when ``role`` is not an explicit, scoped role; else ``None``."""
    if "*" in role:
        return "infra.identity.role_wildcard", f"role '{role}' contains a wildcard"
    if role in PROJECT_WIDE_ROLES:
        return "infra.identity.role_project_wide", f"role '{role}' is a project-wide basic role"
    if not _ROLE_NAME.match(role):
        return "infra.identity.role_invalid", f"role '{role}' is not an explicit role name"
    return None


def _finding(rule: str, message: str, line: int = 1) -> Finding:
    return Finding(IDENTITIES_PATH, line, rule, message)


def _label(identity: ServiceIdentity) -> str:
    return f"{identity.service} in {identity.environment}"


def _coverage(identities: tuple[ServiceIdentity, ...]) -> Iterator[Finding]:
    counts = Counter((i.service, i.environment) for i in identities)
    for (service, environment), count in sorted(counts.items()):
        if count > 1:
            msg = f"{service} in {environment} has {count} rows; one identity per service"
            yield _finding("infra.identity.duplicate", msg)
    for environment in ENVIRONMENT_NAMES:
        for service in SERVICES:
            if (service, environment) not in counts:
                yield _finding("infra.identity.missing", f"no row for {service} in {environment}")


def _roles(identity: ServiceIdentity) -> Iterator[Finding]:
    if not identity.roles:
        yield _finding("infra.identity.roles_empty", f"{_label(identity)} lists no roles")
    for role in identity.roles:
        verdict = judge_role(role)
        if verdict is not None:
            yield _finding(verdict[0], f"{_label(identity)}: {verdict[1]}")
    if identity.service not in TRUTH_READERS:
        for role in sorted(set(identity.roles) & TRUTH_REACHING_ROLES):
            msg = f"{_label(identity)}: role '{role}' could read evaluation ground truth"
            yield _finding("infra.identity.truth_reach", msg)


def _truth_flag(identity: ServiceIdentity) -> Iterator[Finding]:
    if identity.can_read_eval_truth and identity.service not in TRUTH_READERS:
        msg = f"{_label(identity)} may not read evaluation truth; only eval_harness and pipeline"
        yield _finding("infra.identity.truth_flag", msg)


def _impersonation(identity: ServiceIdentity) -> Iterator[Finding]:
    if identity.service != RELEASE_CANDIDATE:
        return
    entries = identity.impersonable_by
    restricted = RC_IMPERSONATION in entries and not any("*" in e for e in entries)
    if not restricted:
        msg = f"{_label(identity)} must be impersonable only through '{RC_IMPERSONATION}'"
        yield _finding("infra.identity.impersonation", msg)


def check_identities(repo_root: Path) -> tuple[Finding, ...]:
    """Rules over ``infra/identities.yaml``; an unreadable file is one finding."""
    try:
        identities = load_identities(repo_root)
    except ConfigError as exc:
        return (_finding("infra.identity.file", f"{exc.path}: {exc.message}"),)
    findings = list(_coverage(identities))
    for identity in identities:
        findings.extend((*_roles(identity), *_truth_flag(identity), *_impersonation(identity)))
    return tuple(findings)


# --- Terraform wiring ---------------------------------------------------------------------------


def identity_service(block: Block) -> str:
    """The service an identity module call is for: its literal ``service``, else its name."""
    service = literal_str(block.get("service"))
    return service if service else block.name.removeprefix("identity_")


def _identity_module_of(expression: str | None) -> str | None:
    match = re.match(r"^module\.(\w+)\.", expression or "")
    return match.group(1) if match else None


def _module_roles(tree: InfraTree, unit: Unit, block: Block) -> Iterator[Finding]:
    roles = literal_list(resolve(unit, block.get("roles")))
    for role in roles or ():
        verdict = judge_role(role)
        if verdict is not None:
            line = tree.attr_line(block, "roles")
            yield Finding(block.file, line, verdict[0], f"{block.name}: {verdict[1]}")


def _duplicate_services(identity_modules: tuple[Block, ...]) -> Iterator[Finding]:
    seen: dict[str, Block] = {}
    for block in identity_modules:
        service = identity_service(block)
        if service in seen:
            msg = f"{block.name} and {seen[service].name} are both the identity of {service}"
            yield Finding(block.file, block.line, "infra.identity.shared", msg)
        else:
            seen[service] = block


def _borrowed_identities(unit: Unit, identity_modules: tuple[Block, ...]) -> Iterator[Finding]:
    owner = {b.name: identity_service(b) for b in identity_modules}
    for call in unit.module_calls("run_service"):
        service = literal_str(call.get("service"))
        used = _identity_module_of(ref_of(call.get("service_account_email")))
        if service and used in owner and owner[used] != service:
            msg = f"{call.name} runs {service} as the identity of {owner[used]}"
            yield Finding(call.file, call.line, "infra.identity.shared", msg)


def _project_grants(tree: InfraTree, unit: Unit) -> Iterator[Finding]:
    for type_name in _IAM_GRANTS:
        for block in unit.resources(type_name):
            role = literal_str(block.get("role"))
            verdict = judge_role(role) if role else None
            if verdict is not None and verdict[0] != "infra.identity.role_invalid":
                line = tree.attr_line(block, "role")
                yield Finding(block.file, line, verdict[0], f"{block.name}: {verdict[1]}")


def check_identity_wiring(tree: InfraTree) -> tuple[Finding, ...]:
    """One identity per service, no borrowed identities, no wildcard or project-wide grants."""
    findings: list[Finding] = []
    for unit in tree.units.values():
        identity_modules = unit.module_calls("service_identity")
        findings.extend(_duplicate_services(identity_modules))
        findings.extend(_borrowed_identities(unit, identity_modules))
        for block in identity_modules:
            findings.extend(_module_roles(tree, unit, block))
        findings.extend(_project_grants(tree, unit))
    return tuple(findings)


def identity_module_names(unit: Unit) -> Mapping[str, str]:
    """``module name -> service`` for every service identity module call in ``unit``."""
    return {b.name: identity_service(b) for b in unit.module_calls("service_identity")}


__all__ = [
    "IDENTITIES_PATH",
    "SERVICES",
    "TRUTH_READERS",
    "ServiceIdentity",
    "check_identities",
    "check_identity_wiring",
    "identity_module_names",
    "identity_service",
    "judge_role",
    "load_identities",
]
