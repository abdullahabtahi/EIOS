"""One place that assembles the governed-action stack for the cockpit API.

Signer, ledger and approval state come from the environment: Cloud KMS and Firestore when
configured, local in-memory implementations only in dev and test (the factories refuse
to start a deployed environment without them).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple

from eios.cockpit.governance_shelf import GovernedActionShelf
from eios.ontology.actions.intent_hub import ActionIntentHub
from eios.ontology.actions.record_store import default_record_store
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.signer import default_action_signer
from eios.ontology.actions.sink import SimulatedWriteBackSink
from eios.ontology.actions.worm import WORMAnchorService

DEMO_SEED_FLAG = "demo_cards_v1"


# [ILLUSTRATIVE] Demo intents proposed through the hub at first load so the shelf opens populated.
# They are signed and ledgered like any other intent; the tag marks them as non-production fixtures.
class _DemoIntent(NamedTuple):
    action_type: str
    parameters: dict[str, Any]
    evidence_refs: list[str]
    requester: str
    propensity: float
    causal_context: dict[str, Any]


_DEMO_INTENTS = (
    _DemoIntent(
        "DeployRetentionConcession",
        {"partner_id": "AP-1029", "rebate_bps": 35, "duration_days": 90, "budget": 18000.0},
        ["ev_churn_decay_882"],
        "PartnerSupervisoryAgent",
        0.84,
        {"partner_churn_hazard": 0.84},
    ),
    _DemoIntent(
        "SuppressCGNATProxyCluster",
        {"entity_id": "CR84920", "hub_degree": 42},
        ["ev_proxy_hub_42"],
        "AMLWorkerAgent",
        0.62,
        {"cgnat_hub_detected": True},
    ),
)


@dataclass(frozen=True)
class GovernanceRuntime:
    sequencer: LedgerSequencer
    hub: ActionIntentHub
    shelf: GovernedActionShelf
    worm: WORMAnchorService

    def seed_demo_intents(self) -> None:
        """Propose the demo intents once across all instances (atomic create-if-absent flag)."""
        if not default_record_store("seed_flags").create(DEMO_SEED_FLAG, {"seeded": True}):
            return
        for spec in _DEMO_INTENTS:
            self.hub.propose_action(
                action_type=spec.action_type,
                parameters=dict(spec.parameters),
                evidence_refs=list(spec.evidence_refs),
                requester_agent_id=spec.requester,
                propensity_score=spec.propensity,
                causal_context=dict(spec.causal_context),
                policy_tags=["ILLUSTRATIVE"],
            )


def build_governance_runtime() -> GovernanceRuntime:
    signer = default_action_signer()
    sequencer = LedgerSequencer()
    hub = ActionIntentHub(
        signer=signer, sequencer=sequencer, sink=SimulatedWriteBackSink(sequencer=sequencer)
    )
    return GovernanceRuntime(
        sequencer=sequencer,
        hub=hub,
        shelf=GovernedActionShelf(intent_hub=hub, signer=signer),
        worm=WORMAnchorService(sequencer=sequencer, signer=signer),
    )
