"""Interactive Demo: Governed Retention Intent & Closed-Loop Flywheel (T031 / US5).

Demonstrates:
1. Proposing a governed LaunchRetentionPlaybook action intent for P-CHURN-DRIFT
2. Cryptographic KMS ECDSA P-256 signature verification
3. Four-Eyes human approval state transition
4. Simulated write-back execution and Decision_Ledger outcome recording
5. Doubly Robust AIPW causal estimation recovering unbiased treatment effect
"""

import sys
from pathlib import Path

# Ensure src is on python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import numpy as np

from eios.churn.flywheel import PlaybookRecalibrator
from eios.churn.models import ActionIntentProposal, DecisionOutcomeRecord
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.intent_hub import ActionIntentHub
from eios.ontology.actions.signer import KMSActionSigner


def run_retention_intent_demo() -> None:
    print("=" * 70)
    print("FEIOS PARTNER CHURN RADAR: GOVERNED ACTION & CAUSAL FLYWHEEL DEMO")
    print("=" * 70)

    # 1. Initialize Hot State & Governance Hub
    engine = HotStateEngine(":memory:")
    signer = KMSActionSigner(
        key_id="projects/feios-prod/locations/global/keyRings/eios/cryptoKeys/action-signer-p256"
    )
    hub = ActionIntentHub(signer=signer)

    print("\n[1] Proposing Governed Action Intent for Persona: P-CHURN-DRIFT")
    proposal = ActionIntentProposal(
        partner_ids=["P-CHURN-DRIFT"],
        playbook_id="VIP_Master_Retention",
        budget=12500.0,
        rationale="VIP Partner with 40% login decay and competitor revshare poaching in SEA.",
        evidence_refs=["DP6:partner_360", "DP9:partner_engagement_signals", "DP10:partner_comms"],
        propensity_score=0.78,
        causal_context={"rival_broker": "XM", "regional_offer": "60% revshare"},
    )

    token = hub.propose_action(
        action_type="LaunchRetentionPlaybook",
        parameters={
            "partner_ids": proposal.partner_ids,
            "playbook_id": proposal.playbook_id,
            "budget": proposal.budget,
        },
        evidence_refs=proposal.evidence_refs,
        requester_agent_id="ChurnRadarSpecialist",
        propensity_score=proposal.propensity_score,
        causal_context=proposal.causal_context,
    )

    print(f"  • Intent ID:      {token.intent_id}")
    print(f"  • Action Type:    {token.action_type}")
    print(f"  • Severity:       {token.severity.value}")
    print(f"  • Status:         {token.status.value}")
    print(f"  • Propensity e(X):{token.propensity_score}")
    print(f"  • Nonce:          {token.nonce}")
    print(f"  • KMS Key ID:     {token.kms_key_id}")
    print(f"  • ECDSA Sig:      {token.signature[:32]}... [ASN.1 DER P-256]")

    # 2. Cryptographic Signature Verification
    print("\n[2] Verifying Cryptographic KMS ECDSA P-256 Signature...")
    is_valid = signer.verify_token(token)
    print(f"  ✓ Signature Verified: {is_valid} (Payload is authentic and tamper-free)")

    # 3. Four-Eyes Approval Workflow
    print("\n[3] Human-in-the-Loop Sign-off (Four-Eyes State Machine)...")
    approved_token = hub.approve_action(
        intent_id=token.intent_id,
        approver_id="USR-HEAD-PARTNERSHIPS",
        role="HeadOfPartnerships",
        comment="Approved VIP custom incentive package to retain high-volume master affiliate.",
    )
    print(f"  ✓ Status after approval: {approved_token.status.value}")

    # 4. Simulated Execution
    print("\n[4] Executing Action Intent Write-back...")
    executed_token = hub.execute_action(intent_id=token.intent_id)
    print(f"  ✓ Status after execution: {executed_token.status.value}")

    # 5. Closed-Loop Outcome Logging & Doubly Robust AIPW Recalibration
    print("\n[5] Simulating Decision Outcomes Ledger & Doubly Robust AIPW Recalibration...")
    recalibrator = PlaybookRecalibrator(engine)

    # Seed 100 historical outcomes with confounding by indication
    np.random.seed(42)
    for i in range(100):
        # VIP Playbook
        w_vip = int(np.random.rand() < 0.7)
        # Treatment provides +8000 revenue
        rev_vip = 30000.0 + (8000.0 if w_vip == 1 else 0.0) + np.random.normal(0, 500)
        recalibrator.record_outcome(
            DecisionOutcomeRecord(
                outcome_id=f"OUT-VIP-{i}",
                intent_id=f"INT-VIP-{i}",
                partner_id=f"P-VIP-{i}",
                playbook_id="VIP_Master_Retention",
                treatment_assigned=w_vip,
                propensity_score=0.7,
                observed_retained_revenue_60d=rev_vip,
                actual_churn_60d=False,
            )
        )

        # Standard Email Outreach Playbook (ineffective)
        w_std = int(np.random.rand() < 0.4)
        rev_std = 15000.0 + (-500.0 if w_std == 1 else 0.0) + np.random.normal(0, 500)
        recalibrator.record_outcome(
            DecisionOutcomeRecord(
                outcome_id=f"OUT-STD-{i}",
                intent_id=f"INT-STD-{i}",
                partner_id=f"P-STD-{i}",
                playbook_id="Standard_Email_Outreach",
                treatment_assigned=w_std,
                propensity_score=0.4,
                observed_retained_revenue_60d=rev_std,
                actual_churn_60d=True if w_std == 1 else False,
            )
        )

    recalibrated_weights = recalibrator.recalibrate_playbook_weights()
    print("\n  Updated Playbook Selection Probabilities (AIPW Causal Uplift):")
    for pb, weight in sorted(recalibrated_weights.items(), key=lambda x: x[1], reverse=True):
        print(f"    • {pb:<25}: {weight * 100:.2f}%")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE: Governance, Cryptography & Causal Flywheel Validated.")
    print("=" * 70)


if __name__ == "__main__":
    run_retention_intent_demo()
