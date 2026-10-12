#!/usr/bin/env python3
"""Runnable Verification Script for Governed Action Intent & Dual Four-Eyes Approval (T045).

Usage:
    python scripts/test_partner_fraud_intent.py --case-id CASE-FRAUD-OPPOSITE-01
"""

import argparse
from eios.ontology.actions.intent_hub import (
    ActionIntentHub,
    ActionSeverity,
    ActionStatus,
    FourEyesApprovalRequiredError,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test partner fraud action intent governance.")
    parser.add_argument("--case-id", default="CASE-FRAUD-OPPOSITE-01", help="Target case identifier")
    args = parser.parse_args()

    print(f"Initializing ActionIntentHub for case {args.case_id}...")
    hub = ActionIntentHub()

    # 1. Propose ClawbackCommission
    print("\n1. Proposing ClawbackCommission intent ($12,500.00 USD)...")
    token = hub.propose_action(
        action_type="ClawbackCommission",
        parameters={"partner_id": "P-FRAUD-RING-01", "period": "2026-Q3", "amount": 12500.0},
        evidence_refs=[f"case/{args.case_id}", "trading_activity/PAIR-EURUSD-01"],
        requester_agent_id="PartnerFraudSpecialist",
    )
    print(f"   Intent ID:       {token.intent_id}")
    print(f"   Severity:        {token.severity.value}")
    print(f"   Status:          {token.status.value}")
    print(f"   Dual Approval:   {token.requires_dual_approval}")
    print(f"   KMS Signature:   {token.signature[:32]}... [ECDSA P-256]")

    # 2. First Approval by Compliance Officer
    print("\n2. Applying 1st Approval (Officer Alice / ComplianceOfficer)...")
    token = hub.approve_action(
        intent_id=token.intent_id,
        approver_id="officer_alice",
        role="ComplianceOfficer",
        comment="Verified opposite trading co-occurrence logs.",
    )
    print(f"   Status:          {token.status.value} (Awaiting 2nd approver)")
    print(f"   Approvals Count: {len(token.approvals)}/2")

    # 3. Attempt Execution with only 1 Approval (Must be blocked!)
    print("\n3. Testing Premature Execution Guard...")
    try:
        hub.execute_action(token.intent_id)
        print("   ERROR: Premature execution was not blocked!")
    except FourEyesApprovalRequiredError:
        print("   ✓ SUCCESS: FourEyesApprovalRequiredError raised - execution blocked!")

    # 4. Second Approval by Senior MLRO
    print("\n4. Applying 2nd Approval (Officer Bob / SeniorMLRO)...")
    token = hub.approve_action(
        intent_id=token.intent_id,
        approver_id="officer_bob",
        role="SeniorMLRO",
        comment="Clawback calculation validated against commission ledger.",
    )
    print(f"   Status:          {token.status.value}")
    print(f"   Approvals Count: {len(token.approvals)}/2 (Fully Approved)")

    # 5. Execute against simulated sink
    print("\n5. Executing Action Intent against Simulated Write-Back Sink...")
    executed_token = hub.execute_action(token.intent_id)
    print(f"   Status:          {executed_token.status.value}")
    print("   ✓ Action successfully recorded in Decision Ledger with immutable audit trail.")


if __name__ == "__main__":
    main()
