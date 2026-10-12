"""No literal project ids, credentials or secrets in ``infra/`` (FR-017, Constitution security).

Environments take their project from a variable supplied outside the repository, and secrets
are only ever referenced. Placeholders (``placeholder-…``, ``REPLACE_ME…``, ``<…>``, empty) are
accepted. Rule ids: ``infra.literal.project_id``, ``.credential``, ``.stored_key``, ``.secret``.
Messages never repeat the offending value.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from tools.common.findings import Finding
from tools.gates.secret_scan import scan_text
from tools.infra_checks.hcl import (
    INFRA_DIR,
    RULE_PARSE,
    Block,
    InfraTree,
    is_placeholder,
    literal_str,
    parse_attributes,
    ref_of,
)
from tools.repo_checks._walk import iter_files, relative_posix

PROJECT_KEYS = frozenset({"project", "project_id"})
CREDENTIAL_KEYS = frozenset(
    {
        "credentials",
        "client_secret",
        "secret_data",
        "password",
        "private_key",
        "api_key",
        "access_token",
        "token",
    }
)
_SERVICE_ACCOUNT = re.compile(r"@([\w-]+)\.iam\.gserviceaccount\.com")
_FILE_CALL = re.compile(r"\bfile\(")


def _judge(key: str, text: str) -> tuple[str, str] | None:
    if is_placeholder(text):
        return None
    if key in PROJECT_KEYS:
        return (
            "infra.literal.project_id",
            f"'{key}' is a literal project id; read it from a variable",
        )
    account = _SERVICE_ACCOUNT.search(text)
    if account and not is_placeholder(account.group(1)):
        return (
            "infra.literal.project_id",
            f"'{key}' embeds a literal project id in a service account",
        )
    if key.lower() in CREDENTIAL_KEYS:
        return "infra.literal.credential", f"'{key}' is a literal credential; reference a secret"
    return None


def _leaves(value: Any, key: str) -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from _leaves(child, str(child_key))
    elif isinstance(value, list):
        for child in value:
            yield from _leaves(child, key)
    else:
        yield key, value


def _verdict(key: str, value: Any) -> tuple[str, str] | None:
    text = literal_str(value)
    if text is not None:
        return _judge(key, text)
    expression = ref_of(value)
    if key.lower() in CREDENTIAL_KEYS and expression and _FILE_CALL.search(expression):
        return "infra.literal.credential", f"'{key}' reads a credential file; use workload identity"
    return None


def _block_literals(tree: InfraTree, block: Block) -> Iterator[Finding]:
    if block.kind == "resource" and block.labels[:1] == ("google_service_account_key",):
        msg = "a stored service account key; use keyless federation or impersonation"
        yield Finding(block.file, block.line, "infra.literal.stored_key", msg)
    for key, value in _leaves(dict(block.body), ""):
        effective = block.name if block.kind == "variable" and key == "default" else key
        verdict = _verdict(effective, value)
        if verdict is not None:
            yield Finding(block.file, tree.attr_line(block, key), verdict[0], verdict[1])


def _tfvars(repo_root: Path) -> Iterator[Finding]:
    for path in iter_files(repo_root, start=INFRA_DIR):
        if ".tfvars" not in path.name:
            continue
        name = relative_posix(repo_root, path)
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            attributes = parse_attributes(text)
        except ValueError as exc:
            yield Finding(name, 1, RULE_PARSE, str(exc))
            continue
        lines = text.splitlines()
        for key, value in attributes.items():
            verdict = _verdict(key, value)
            if verdict is not None:
                yield Finding(name, _line_of(lines, key), verdict[0], verdict[1])


def _line_of(lines: list[str], key: str) -> int:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    return next((i for i, line in enumerate(lines, start=1) if pattern.match(line)), 1)


def _secret_shapes(repo_root: Path) -> Iterator[Finding]:
    for path in iter_files(repo_root, start=INFRA_DIR):
        name = relative_posix(repo_root, path)
        text = path.read_text(encoding="utf-8", errors="replace")
        for found in scan_text(name, text):
            yield Finding(name, found.line, "infra.literal.secret", found.message)


def check_literals(repo_root: Path, tree: InfraTree) -> tuple[Finding, ...]:
    """Literal project ids, credentials, stored keys and secret-shaped text under ``infra/``."""
    root = repo_root.resolve()
    findings: list[Finding] = []
    for unit in tree.units.values():
        for block in unit.blocks:
            findings.extend(_block_literals(tree, block))
    findings.extend(_tfvars(root))
    findings.extend(_secret_shapes(root))
    return tuple(findings)
