"""Constitution VI on the Terraform side: who may be granted read access to evaluation truth.

The truth module's grants are label-to-member maps. Each member must be the ``member`` output of a
service identity module, and that service must be allowed by ``infra/identities.yaml``: the open
splits (``reader_members``) need ``can_read_eval_truth``; the sealed split
(``sealed_reader_members``) is for the release-candidate identity only. The module's buckets must
stay private. Rule ids: ``infra.eval_truth.grant``, ``.unknown_reader``, ``.literal_principal``,
``.not_restricted``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from tools.common.findings import Finding
from tools.infra_checks.hcl import Block, InfraTree, Unit, literal_str, ref_of
from tools.infra_checks.identities import (
    RELEASE_CANDIDATE,
    ServiceIdentity,
    identity_module_names,
)

TRUTH_MODULE = "eval_truth_store"
OPEN_ATTR = "reader_members"
SEALED_ATTR = "sealed_reader_members"
_MEMBER_REF = re.compile(r"^module\.(\w+)\.\w+$")
_BUCKET_GRANTS = ("google_storage_bucket_iam_member", "google_storage_bucket_iam_binding")


def _truth_flags(identities: Sequence[ServiceIdentity]) -> Mapping[tuple[str, str], bool]:
    return {(i.service, i.environment): i.can_read_eval_truth for i in identities}


def _line(tree: InfraTree, block: Block, label: str) -> int:
    return tree.attr_line(block, label)


def _judge_member(
    tree: InfraTree,
    block: Block,
    unit: Unit,
    flags: Mapping[tuple[str, str], bool] | None,
    split: str,
    pair: tuple[str, Any],
) -> Iterator[Finding]:
    label, value = pair
    line = _line(tree, block, label)
    text = literal_str(value)
    if text is not None:
        msg = f"{split} grant '{label}' is a literal principal; use a service identity member"
        yield Finding(block.file, line, "infra.eval_truth.literal_principal", msg)
        return
    match = _MEMBER_REF.match(ref_of(value) or "")
    service = identity_module_names(unit).get(match.group(1)) if match else None
    if service is None:
        msg = f"{split} grant '{label}' does not resolve to a service identity module"
        yield Finding(block.file, line, "infra.eval_truth.unknown_reader", msg)
        return
    if flags is not None and not _allowed(flags, service, unit.name, split):
        rule = "infra.eval_truth.grant"
        yield Finding(block.file, line, rule, _denied(service, unit.name, split))


def _allowed(flags: Mapping[tuple[str, str], bool], service: str, env: str, split: str) -> bool:
    if split == "sealed":
        return service == RELEASE_CANDIDATE
    return flags.get((service, env), False)


def _denied(service: str, env: str, split: str) -> str:
    if split == "sealed":
        return f"{service} may not read the sealed split in {env}; only {RELEASE_CANDIDATE}"
    return f"{service} may not read evaluation truth in {env} (can_read_eval_truth is not true)"


def _module_call_grants(
    tree: InfraTree, unit: Unit, flags: Mapping[tuple[str, str], bool] | None
) -> Iterator[Finding]:
    for call in unit.module_calls(TRUTH_MODULE):
        for attr, split in ((OPEN_ATTR, "open"), (SEALED_ATTR, "sealed")):
            members = call.get(attr)
            if members is None:
                continue
            if not isinstance(members, dict):
                msg = f"{attr} is not a literal map, so its readers cannot be proven"
                yield Finding(
                    call.file, _line(tree, call, attr), "infra.eval_truth.unknown_reader", msg
                )
                continue
            for pair in members.items():
                yield from _judge_member(tree, call, unit, flags, split, pair)


def _resource_grants(
    tree: InfraTree, unit: Unit, flags: Mapping[tuple[str, str], bool] | None
) -> Iterator[Finding]:
    for type_name in _BUCKET_GRANTS:
        for block in unit.resources(type_name):
            bucket = ref_of(block.get("bucket")) or ""
            if TRUTH_MODULE not in bucket:
                continue
            split = "sealed" if "sealed" in bucket else "open"
            yield from _judge_member(
                tree, block, unit, flags, split, (block.name, block.get("member"))
            )


def _module_grants(tree: InfraTree, module: Unit) -> Iterator[Finding]:
    for type_name in _BUCKET_GRANTS:
        for block in module.resources(type_name):
            member = block.get("member")
            members = member if isinstance(member, list) else [member]
            if any(literal_str(m) is not None for m in members):
                msg = f"{block.name} grants a literal principal on the eval-truth buckets"
                line = _line(tree, block, "member")
                yield Finding(block.file, line, "infra.eval_truth.literal_principal", msg)


def _restricted(tree: InfraTree, module: Unit) -> Iterator[Finding]:
    for bucket in module.resources("google_storage_bucket"):
        checks = (
            ("uniform_bucket_level_access", True),
            ("public_access_prevention", '"enforced"'),
        )
        for attr, expected in checks:
            if bucket.get(attr) != expected:
                msg = f"bucket {bucket.name} must set {attr} = {str(expected).strip(chr(34))}"
                line = _line(tree, bucket, attr)
                yield Finding(bucket.file, line, "infra.eval_truth.not_restricted", msg)


def check_eval_truth(tree: InfraTree, identities: Sequence[ServiceIdentity]) -> tuple[Finding, ...]:
    """Grants on the evaluation-truth buckets, and the buckets' own privacy settings.

    Without any identity rows the flag-based grant rule is skipped (the identities check reports
    the missing file); every structural rule still applies.
    """
    flags = _truth_flags(identities) if identities else None
    findings: list[Finding] = []
    for unit in tree.envs.values():
        findings.extend(_module_call_grants(tree, unit, flags))
        findings.extend(_resource_grants(tree, unit, flags))
    module = tree.modules.get(TRUTH_MODULE)
    if module is not None:
        findings.extend(_module_grants(tree, module))
        findings.extend(_restricted(tree, module))
    return tuple(findings)
