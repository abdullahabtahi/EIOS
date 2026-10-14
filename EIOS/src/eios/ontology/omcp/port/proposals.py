"""Proposals (spec 023 FR-005, FR-013): drafts a human stages, never signed, staged, approved or executed here.

The closed set of kinds is the assistant's vocabulary. Each maps to the one action name the decision-governance
component (the intent hub) already owns, so the UI and the hub never invent a second vocabulary. That hub name is
an internal constant: it is used when a human stages the draft and never appears in a result an operator reads.
"""

import hashlib
from enum import StrEnum

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.aml_fixtures import PENDING_WITHDRAWALS
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.entities import EntityKind
from eios.ontology.omcp.port.partner_fixtures import STORY_PARTNER
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
    signed: bool = False
    staged: bool = False
    next_step: str = _NEXT_STEP


class ProposeDealArgs(StrictModel):
    entity_id: str
    playbook_id: str


class ProposeHoldArgs(StrictModel):
    entity_id: str


def _ref(kind: ProposalKind, entity_id: str, key: str) -> str:
    return "prop-" + hashlib.sha256(f"{kind.value}|{entity_id}|{key}".encode()).hexdigest()[:10]


def propose_partner_action(ctx: ReadModels, _who: Principal, args: ProposeDealArgs) -> Proposal:
    partner = ctx.directory.resolve(args.entity_id, EntityKind.PARTNER).entity_id
    if partner != STORY_PARTNER:
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
        "Four-eyes: a second approver is required (over the fast-path budget)"
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
    pending = PENDING_WITHDRAWALS.get(account)
    if pending is None:
        raise PortError(ToolErrorCode.NOT_FOUND, f"no pending withdrawal for {account}")
    return Proposal(
        **envelope(
            ctx,
            "action.propose_hold",
            account,
            "port.aml_fixtures.PENDING_WITHDRAWALS",
            {
                "estimated_cost_usd": "USD",
                "expected_effect_low": "USD",
                "expected_effect_high": "USD",
            },
            (SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE),
        ),
        proposal_ref=_ref(ProposalKind.HOLD_WITHDRAWAL, account, pending.withdrawal_id),
        kind=ProposalKind.HOLD_WITHDRAWAL,
        label=LABELS[ProposalKind.HOLD_WITHDRAWAL],
        offer=f"Hold withdrawal {pending.withdrawal_id} on account {account}",
        estimated_cost_usd=0.0,
        expected_effect_low=pending.amount_usd,
        expected_effect_high=pending.amount_usd,
        expected_effect_basis="The full pending withdrawal stays in the account until review",
        approval_requirement="Four-eyes: a second approver is required",
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
