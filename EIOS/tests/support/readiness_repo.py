"""Trees for the readiness tests: a specs dir, spike records, an ADR index and a register."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import yaml

DEPENDENCIES_RELATIVE = "specs/003-ontology-metrics/dependencies.yaml"
REGISTER_RELATIVE = "docs/feature_register.yaml"
INDEX_RELATIVE = "docs/spikes_and_adrs.md"
FEATURE_IDS = tuple(f"F{n:02d}" for n in range(16))


@dataclass(frozen=True)
class ReadinessScenario:
    """What a throwaway repository says about one feature's dependencies."""

    feature: str = "F03"
    depends_on_features: Sequence[str] = ()
    depends_on_spikes: Sequence[str] = ()
    depends_on_adrs: Sequence[str] = ()
    spike_states: Mapping[str, str] = field(default_factory=dict)  # record file: open/closed
    index_only_spikes: Sequence[str] = ()  # in the spike table but without a record file
    adr_statuses: Mapping[str, str] = field(default_factory=dict)
    complete_features: Sequence[str] = ()


def dependencies_text(
    feature: str, features: Sequence[str], spikes: Sequence[str], adrs: Sequence[str]
) -> str:
    return yaml.safe_dump(
        {
            "feature": feature,
            "depends_on_features": list(features),
            "depends_on_spikes": list(spikes),
            "depends_on_adrs": list(adrs),
        }
    )


def register_text(complete: Sequence[str]) -> str:
    entries = [{"id": f, "name": f"{f}-name", "complete": f in complete} for f in FEATURE_IDS]
    return yaml.safe_dump({"features": entries})


def index_text(adr_statuses: Mapping[str, str], spike_ids: Sequence[str] = ()) -> str:
    # The index parsers reject an empty table, so an unrelated spike and ADR are always listed.
    spikes = "".join(f"| **{s}** | q | w | m | u | f |\n" for s in (*spike_ids, "S-99"))
    listed = {**adr_statuses, "ADR-999": "Open"}
    adrs = "".join(f"| {a} | Decision {a} | {s} | lean | — |\n" for a, s in listed.items())
    return (
        "# Spikes and ADRs\n\n## 1. Spikes\n\n"
        "| ID | Question | Why unverified | Method | Decision it unlocks | Fallback |\n"
        "|---|---|---|---|---|---|\n" + spikes + "\n## 2. ADR index\n\n"
        "| ADR | Decision | Status | Default / current lean | Depends on |\n"
        "|---|---|---|---|---|\n" + adrs
    )


def spike_record(spike_id: str, state: str) -> str:
    base = f"# {spike_id}: A question\nId: {spike_id}\nQuestion: Why?\nTime box: 1 day [TARGET]\n"
    base += f"Owner: platform-team\nState: {state}\n"
    if state == "closed":
        base += (
            "Linked ADR: ADR-002\nMethod: m\nData: d\nResult: r\nDecision: x\nDate: 2026-01-01\n"
        )
    return base


def readiness_tree(scenario: ReadinessScenario, prefix: str = "") -> dict[str, str]:
    """Files (relative path -> text) for ``scenario``; ``prefix`` places them in a subdirectory."""
    s = scenario
    all_spikes = [*s.spike_states, *s.index_only_spikes]
    tree = {
        DEPENDENCIES_RELATIVE: dependencies_text(
            s.feature, s.depends_on_features, s.depends_on_spikes, s.depends_on_adrs
        ),
        REGISTER_RELATIVE: register_text(s.complete_features),
        INDEX_RELATIVE: index_text(s.adr_statuses, all_spikes),
    }
    for spike_id, state in s.spike_states.items():
        tree[f"docs/adr/{spike_id}-record.md"] = spike_record(spike_id, state)
    return {f"{prefix}{path}": text for path, text in tree.items()}
