"""The readiness rule: every dependency a feature declares is met before it starts.

Ready only when every ``depends_on_spikes`` entry is ``closed``, every ``depends_on_adrs``
entry is ``Accepted`` and every ``depends_on_features`` entry is complete in the register.
Anything not found anywhere is blocked with the state ``not found``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from eios.common.errors import ConfigError
from tools.common.findings import Finding
from tools.common.yaml_io import load_validated
from tools.readiness.states import (
    NOT_FOUND,
    adr_statuses,
    feature_completeness,
    spike_states,
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "feature-dependencies.schema.json"
DECLARATION_GLOB = "*/dependencies.yaml"
ADR_ACCEPTED = "Accepted"
SPIKE_CLOSED = "closed"


@dataclass(frozen=True)
class Declaration:
    """A feature's declared dependencies and the file that declares them."""

    feature: str
    path: str
    features: tuple[str, ...]
    spikes: tuple[str, ...]
    adrs: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessResult:
    """Outcome for one feature: unmet dependencies as findings, plus every dependency's state."""

    feature: str
    findings: tuple[Finding, ...]
    states: Mapping[str, str]

    @property
    def ready(self) -> bool:
        return not self.findings


def _specs_dir(repo_root: Path) -> Path:
    """``specs/`` under the root, else beside it (the planning tree sits next to FEIOS)."""
    for candidate in (repo_root / "specs", repo_root.parent / "specs"):
        if candidate.is_dir():
            return candidate
    raise ConfigError("specs", "$", f"no specs directory under or beside {repo_root}")


def _load_declaration(path: Path, repo_root: Path) -> Declaration:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    data = cast("dict[str, Any]", load_validated(path, schema))  # shape fixed by the schema
    try:
        shown = path.relative_to(repo_root).as_posix()
    except ValueError:
        shown = str(path)
    return Declaration(
        feature=str(data["feature"]),
        path=shown,
        features=tuple(data["depends_on_features"]),
        spikes=tuple(data["depends_on_spikes"]),
        adrs=tuple(data["depends_on_adrs"]),
    )


def find_declaration(repo_root: Path, feature: str) -> Declaration:
    """The one validated ``dependencies.yaml`` that declares ``feature``."""
    paths = sorted(_specs_dir(repo_root).glob(DECLARATION_GLOB))
    found = [d for d in (_load_declaration(p, repo_root) for p in paths) if d.feature == feature]
    if not found:
        raise ConfigError("specs", "$", f"no dependencies.yaml declares feature {feature}")
    if len(found) > 1:
        where = ", ".join(d.path for d in found)
        raise ConfigError(
            found[0].path, "feature", f"{feature} is declared more than once: {where}"
        )
    return found[0]


def _unmet(
    decl: Declaration,
    spikes: Mapping[str, str],
    adrs: Mapping[str, str],
    features: Mapping[str, bool],
) -> tuple[list[Finding], dict[str, str]]:
    findings: list[Finding] = []
    states: dict[str, str] = {}

    def add(rule: str, dep: str, state: str, kind: str, need: str) -> None:
        states[dep] = state
        message = f"{decl.feature} depends on {kind} {dep}, which is {state} (needs {need})"
        findings.append(Finding(decl.path, 1, f"readiness.{rule}", message))

    for spike in decl.spikes:
        state = spikes.get(spike, NOT_FOUND)
        states[spike] = state
        if state != SPIKE_CLOSED:
            add("spike_open", spike, state, "spike", SPIKE_CLOSED)
    for adr in decl.adrs:
        status = adrs.get(adr, NOT_FOUND)
        states[adr] = status
        if status != ADR_ACCEPTED:
            add("adr_not_accepted", adr, status, "ADR", ADR_ACCEPTED)
    for dep in decl.features:
        done = features.get(dep)
        state = NOT_FOUND if done is None else ("complete" if done else "incomplete")
        states[dep] = state
        if not done:
            add("feature_incomplete", dep, state, "feature", "complete")
    return findings, states


def check_readiness(repo_root: Path, feature: str) -> ReadinessResult:
    """Evaluate ``feature``'s declared dependencies against the current records."""
    root = repo_root.resolve()
    decl = find_declaration(root, feature)
    spikes = spike_states(root) if decl.spikes else {}
    adrs = adr_statuses(root) if decl.adrs else {}
    features = feature_completeness(root) if decl.features else {}
    findings, states = _unmet(decl, spikes, adrs, features)
    return ReadinessResult(feature, tuple(findings), states)
