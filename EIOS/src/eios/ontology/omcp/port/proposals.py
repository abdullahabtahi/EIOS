"""Proposals (spec 023 FR-005, FR-013): drafts a human stages, never signed, staged, approved or executed here.

The closed set of kinds is the assistant's vocabulary. Each maps to the one action name the decision-governance
component (the intent hub) already owns, so the UI and the hub never invent a second vocabulary. That hub name is
an internal constant: it is used when a human stages the draft and never appears in a result an operator reads.
"""

import hashlib
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.entities import EntityKind
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import ToolSpec


class ProposalKind(StrEnum):
    HOLD_WITHDRAWAL = "hold_withdrawal"
    RETENTION_DEAL = "retention_deal"


KIND_TO_HUB_ACTION = {
    ProposalKind.HOLD_WITHDRAWAL: "HoldWithdrawal",
    ProposalKind.RETENTION_DEAL: "LaunchRetentionPlaybook",
}
LABELS = {
    ProposalKind.HOLD_WITHDRAWAL: "Hold a pending withdrawal for review",
    ProposalKind.RETENTION_DEAL: "Offer a retention deal",
}
_RANGE = 0.25  # [ASSUMPTION] no interval is modelled for deal uplift yet; the range is +/-25% of the point value
_NEXT_STEP = (
    "A human must stage this through the Governed Action Shelf; nothing has been signed or sent."
)


class Proposal(ToolResult):
    proposal_ref: str
    kind: ProposalKind
    label: str
    offer: str
    estimated_cost_usd: float
    expected_effect_low: float
    expected_effect_high: float
    expected_effect_basis: str
    approval_requirement: str
    withdrawal_id: str | None = (
        None  # a hold names the withdrawal it holds; the stage request reads it
    )
    signed: bool = False
    staged: bool = False
    next_step: str = _NEXT_STEP


_HOLD_REASON = "Held for review on the assistant's proposal"
_HOLD_SEVERITY = "HIGH"
_DEAL_SEVERITY = "MEDIUM"


def hold_stage_request(
    entity_id: str, withdrawal_id: str, reason: str = _HOLD_REASON
) -> dict[str, Any]:
    """The request that stages a hold on one pending withdrawal. A hold needs the withdrawal id, not the account id."""
    return {
        "action_type": KIND_TO_HUB_ACTION[ProposalKind.HOLD_WITHDRAWAL],
        "target_entity_id": entity_id,
        "severity": _HOLD_SEVERITY,
        "requires_four_eyes": True,
        "metadata": {"txn_id": withdrawal_id, "reason": reason},
    }


def stage_request(proposal: Proposal, args: Mapping[str, Any]) -> dict[str, Any]:
    """The request a human's click sends to the stage endpoint: the hub's action name and its required parameters.

    Built here, beside `KIND_TO_HUB_ACTION`, so the browser forwards it unchanged and never invents a vocabulary or
    guesses which id a parameter wants (a hold needs the withdrawal id, not the account id). It is kept out of the
    result the model reads. Staging it is a human act; nothing here signs, stages or approves.
    """
    entity = proposal.entity_id
    if entity is None:
        raise ValueError("a proposal names the entity it is about")
    if proposal.kind is ProposalKind.HOLD_WITHDRAWAL:
        if proposal.withdrawal_id is None:
            raise ValueError("a hold proposal names the withdrawal it holds")
        return hold_stage_request(entity, proposal.withdrawal_id)
    metadata = {
        "partner_ids": [entity],
        "playbook_id": args["playbook_id"],
        "budget": proposal.estimated_cost_usd,
    }
    severity, dual = _DEAL_SEVERITY, proposal.approval_requirement.startswith("Dual")
    return {
        "action_type": KIND_TO_HUB_ACTION[proposal.kind],
        "target_entity_id": entity,
        "severity": severity,
        "requires_four_eyes": dual,
        "metadata": metadata,
    }


class ProposeDealArgs(StrictModel):
    entity_id: str
    playbook_id: str


class ProposeHoldArgs(StrictModel):
    entity_id: str


def _ref(kind: ProposalKind, entity_id: str, key: str) -> str:
    return "prop-" + hashlib.sha256(f"{kind.value}|{entity_id}|{key}".encode()).hexdigest()[:10]


def propose_partner_action(ctx: ReadModels, _who: Principal, args: ProposeDealArgs) -> Proposal:
    partner = ctx.directory.resolve(args.entity_id, EntityKind.PARTNER).entity_id
    if not ctx.partner.has_detail(partner):
        raise PortError(
            ToolErrorCode.DATA_UNAVAILABLE, f"no retention deals are defined for {partner} yet"
        )
    deals = {d.playbook_id: d for d in ctx.partner.get_retention_playbooks(partner)}
    deal = deals.get(args.playbook_id)
    if deal is None:
        raise PortError(ToolErrorCode.NOT_FOUND, "no such retention deal for this partner")
    name = next(
        p.name for p in ctx.partner.get_churn_radar_scatter().partners if p.partner_id == partner
    )
    uplift = deal.projected_retention_uplift_pct
    approval = (
        "Dual approval: a second approver is required (over the fast-path budget)"
        if deal.requires_four_eyes
        else "Fast path: one approver (within the fast-path budget)"
    )
    return Proposal(
        **envelope(
            ctx,
            "action.propose_partner",
            partner,
            "cockpit.partner.get_retention_playbooks",
            {
                "estimated_cost_usd": "USD",
                "expected_effect_low": "percent",
                "expected_effect_high": "percent",
            },
            (SecurityMarking.PARTNER_COMMERCIAL,),
            origin=ctx.partner_origin,
        ),
        proposal_ref=_ref(ProposalKind.RETENTION_DEAL, partner, deal.playbook_id),
        kind=ProposalKind.RETENTION_DEAL,
        label=LABELS[ProposalKind.RETENTION_DEAL],
        offer=f"{deal.title} to {name}",
        estimated_cost_usd=deal.estimated_cost_usd,
        expected_effect_low=round(uplift * (1 - _RANGE), 1),
        expected_effect_high=round(uplift * (1 + _RANGE), 1),
        expected_effect_basis="ASSUMPTION: plus or minus a quarter around the playbook's projected retention uplift",
        approval_requirement=approval,
    )


def propose_hold(ctx: ReadModels, _who: Principal, args: ProposeHoldArgs) -> Proposal:
    account = ctx.directory.resolve(args.entity_id, EntityKind.ACCOUNT).entity_id
    pending = ctx.aml.get_pending_withdrawal(account)
    if pending is None:
        raise PortError(ToolErrorCode.NOT_FOUND, f"no pending withdrawal for {account}")
    return Proposal(
        **envelope(
            ctx,
            "action.propose_hold",
            account,
            "cockpit.aml.get_pending_withdrawal",
            {
                "estimated_cost_usd": "USD",
                "expected_effect_low": "USD",
                "expected_effect_high": "USD",
            },
            (SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE),
            origin=ctx.aml_origin,
        ),
        proposal_ref=_ref(ProposalKind.HOLD_WITHDRAWAL, account, pending.withdrawal_id),
        withdrawal_id=pending.withdrawal_id,
        kind=ProposalKind.HOLD_WITHDRAWAL,
        label=LABELS[ProposalKind.HOLD_WITHDRAWAL],
        offer=f"Hold withdrawal {pending.withdrawal_id} on account {account}",
        estimated_cost_usd=0.0,
        expected_effect_low=pending.amount_usd,
        expected_effect_high=pending.amount_usd,
        expected_effect_basis="The full pending withdrawal stays in the account until review",
        approval_requirement="Dual approval: a second approver is required",
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "propose_partner_action",
        "action.propose_partner",
        "propose",
        (Workstation.PARTNER_MANAGER,),
        ProposeDealArgs,
        Proposal,
        propose_partner_action,
        300.0,
        (SecurityMarking.PARTNER_COMMERCIAL,),
    ),
    ToolSpec(
        "propose_hold",
        "action.propose_hold",
        "propose",
        (Workstation.AML_INVESTIGATOR,),
        ProposeHoldArgs,
        Proposal,
        propose_hold,
        300.0,
        (SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE),
    ),
)
