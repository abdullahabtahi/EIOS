"""Static policy rules over the Terraform tree: module shape, prod-like posture, signing key.

Rule ids: ``infra.module.no_variables``, ``infra.module.no_outputs``,
``infra.prod_like.min_instances``, ``infra.prod_like.signing_key``,
``infra.kms.signing_algorithm``. The eval-truth rules live in ``truth`` and are re-exported here.
"""

from __future__ import annotations

from collections.abc import Iterator

from tools.common.findings import Finding
from tools.infra_checks.hcl import (
    Block,
    InfraTree,
    Unit,
    literal_str,
    number_of,
    resolve,
)
from tools.infra_checks.truth import check_eval_truth

PROD_LIKE = "prod-like"
SECRET_STORE = "secret_store"  # noqa: S105
SIGNING_PURPOSE = "ASYMMETRIC_SIGN"
SIGNING_ALGORITHM = "EC_SIGN_P256_SHA256"
KMS_KEY = "google_kms_crypto_key"


def check_module_structure(tree: InfraTree) -> tuple[Finding, ...]:
    """Every module directory with Terraform in it declares variables and outputs."""
    findings: list[Finding] = []
    for unit in tree.modules.values():
        for kind, rule in (("variable", "no_variables"), ("output", "no_outputs")):
            if not unit.of_kind(kind):
                msg = f"module '{unit.name}' declares no {kind}s in any file"
                findings.append(Finding(unit.directory, 0, f"infra.module.{rule}", msg))
    return tuple(findings)


# --- prod-like ----------------------------------------------------------------------------------


def _min_instances(tree: InfraTree, unit: Unit, call: Block) -> Iterator[Finding]:
    if call.get("stateful") is False:
        return
    if "min_instances" not in call.body:
        msg = f"{call.name} does not set min_instances; stateful services stay warm in prod-like"
        yield Finding(call.file, call.line, "infra.prod_like.min_instances", msg)
        return
    value = resolve(unit, call.get("min_instances"))
    line = tree.attr_line(call, "min_instances")
    count = number_of(value)
    if count is None:
        msg = f"{call.name} min_instances cannot be proven to be at least 1"
        yield Finding(call.file, line, "infra.prod_like.min_instances", msg)
    elif count < 1:
        msg = f"{call.name} sets min_instances = {count}; prod-like needs at least 1"
        yield Finding(call.file, line, "infra.prod_like.min_instances", msg)


def _is_signing_key(block: Block) -> bool:
    return literal_str(block.get("purpose")) == SIGNING_PURPOSE


def _has_signing_key(unit: Unit | None) -> bool:
    return unit is not None and any(_is_signing_key(b) for b in unit.resources(KMS_KEY))


def _signing_key(tree: InfraTree, unit: Unit) -> Iterator[Finding]:
    if any(_is_signing_key(b) for b in unit.resources(KMS_KEY)):
        return
    calls = unit.module_calls(SECRET_STORE)
    rule = "infra.prod_like.signing_key"
    if not calls:
        yield Finding(
            unit.directory, 0, rule, "prod-like has no secret_store module and no signing key"
        )
        return
    module = tree.modules.get(SECRET_STORE)
    for call in calls:
        line = tree.attr_line(call, "signing_key_enabled")
        if resolve(unit, call.get("signing_key_enabled")) is not True:
            yield Finding(call.file, line, rule, "signing_key_enabled must be true in prod-like")
        elif not _has_signing_key(module):
            msg = "the secret_store module defines no ASYMMETRIC_SIGN key to enable"
            yield Finding(call.file, line, rule, msg)


def check_prod_like(tree: InfraTree) -> tuple[Finding, ...]:
    """prod-like keeps stateful services warm and has an asymmetric signing key (FR-015)."""
    unit = tree.envs.get(PROD_LIKE)
    if unit is None:
        return ()
    findings: list[Finding] = []
    for call in unit.module_calls("run_service"):
        findings.extend(_min_instances(tree, unit, call))
    findings.extend(_signing_key(tree, unit))
    findings.extend(_signing_algorithms(tree))
    return tuple(findings)


def _algorithm(block: Block) -> tuple[str | None, str]:
    template = block.get("version_template")
    bodies = template if isinstance(template, list) else [template]
    for body in bodies:
        if isinstance(body, dict) and "algorithm" in body:
            return literal_str(body["algorithm"]), "algorithm"
    return None, "algorithm"


def _signing_algorithms(tree: InfraTree) -> Iterator[Finding]:
    for unit in tree.units.values():
        for block in unit.resources(KMS_KEY):
            algorithm, attr = _algorithm(block)
            if _is_signing_key(block) and algorithm not in (None, SIGNING_ALGORITHM):
                msg = (
                    f"signing key {block.name} uses {algorithm}; "
                    f"Action Intents need {SIGNING_ALGORITHM}"
                )
                yield Finding(
                    block.file, tree.attr_line(block, attr), "infra.kms.signing_algorithm", msg
                )


__all__ = ["check_eval_truth", "check_module_structure", "check_prod_like"]
