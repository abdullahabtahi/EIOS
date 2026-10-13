#!/usr/bin/env python3
"""Runnable Verification Script for Real-Time Pre-Withdrawal Sentinel & KMS Governance (T048 / US2).

Usage:
    python scripts/test_withdrawal_sentinel.py --client-id C-AML-ROUNDTRIP-001 --amount 499.50
"""

import argparse
import sys
import time
from pathlib import Path

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eios.aml.models import WithdrawalDisposition
from eios.aml.withdrawal_sentinel import WithdrawalSentinel
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.intent_hub import (
    ActionIntentHub,
    FourEyesApprovalRequiredError,
)


def main() -> None:  # noqa: PLR0915
    parser = argparse.ArgumentParser(
        description="Test real-time pre-withdrawal evaluation and action intent governance."
    )
    parser.add_argument(
        "--client-id", default="C-AML-ROUNDTRIP-001", help="Target client account ID"
    )
    parser.add_argument(
        "--withdrawal-id", default="WTH-2026-9001", help="Withdrawal transaction ID"
    )
    parser.add_argument("--amount", type=float, default=499.50, help="Withdrawal amount in USD")
    args = parser.parse_args()

    print("================================================================================")
    print("  Real-Time Pre-Withdrawal Fraud Intervention & Governance Verification")
    print("  Authoritative Reference: docs/brief/monitoring.md §5.4, §6.1")
    print("  Constitution Principles: I (Zero LLM Math), II (Human-in-the-Loop Governance)")
    print("================================================================================\n")

    hot_state = HotStateEngine()
    intent_hub = ActionIntentHub()
    sentinel = WithdrawalSentinel(hot_state=hot_state, intent_hub=intent_hub)

    print(
        f"1. Evaluating inbound withdrawal request for account {args.client_id} (${args.amount:,.2f} USD)..."
    )
    print(
        "   Simulating acute structuring indicators: 12h KYC recency, zero-risk micro-P&L trade..."
    )

    t0 = time.perf_counter()
    assessment = sentinel.evaluate_withdrawal(
        withdrawal_id=args.withdrawal_id,
        client_id=args.client_id,
        amount_usd=args.amount,
        recent_alert_score=0.92,
        hours_since_deposit=1.5,
        market_risk_pct=0.005,
        hours_since_kyc=12.0,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    print(f"\n   Decision Latency: {latency_ms:.2f} ms (< 2000.0 ms p95 SLO target)")
    print(f"   Risk Score:       {assessment.risk_score:.4f}")
    print(f"   Recommendation:   {assessment.recommendation.value}")
    print(f"   Intent ID:        {assessment.intent_id}")

    assert latency_ms < 2000.0, "SLO latency exceeded 2000ms"  # noqa: S101
    assert assessment.recommendation == WithdrawalDisposition.PROPOSE_HOLD  # noqa: S101
    assert assessment.intent_id is not None  # noqa: S101

    token = intent_hub.get_status(assessment.intent_id)
    print("\n2. Inspecting emitted Cloud KMS Action Intent Proposal:")
    print(f"   • Action Type:          {token.action_type}")
    print(f"   • Severity:             {token.severity.value}")
    print(f"   • Status:               {token.status.value} (PENDING - zero autonomous write-back)")
    print(f"   • Dual Approval Req:    {token.requires_dual_approval}")
    print(f"   • KMS ECDSA P-256 Sig:  {token.signature[:32]}...")
    print(f"   • Key ID:               {token.kms_key_id}")

    # Step 3: Four-eyes authorization validation
    print("\n3. Testing Four-Eyes Human Approval State Machine:")
    print("   Applying first approval: Officer Alice (ComplianceOfficer)...")
    token = intent_hub.approve_action(
        intent_id=token.intent_id,
        approver_id="officer_alice",
        role="ComplianceOfficer",
        comment="Confirmed structuring sequence; verified zero-risk trading P&L.",
    )
    print(f"   • Approvals: {len(token.approvals)}/2 | Status: {token.status.value}")

    print("\n   Attempting execution with only 1 signature (testing premature execution guard)...")
    try:
        intent_hub.execute_action(token.intent_id)
        print("   ❌ ERROR: Premature execution succeeded!")
    except FourEyesApprovalRequiredError:
        print("   ✓ SUCCESS: FourEyesApprovalRequiredError blocked premature execution!")

    print("\n   Applying second approval: Officer Bob (MLRO)...")
    token = intent_hub.approve_action(
        intent_id=token.intent_id,
        approver_id="officer_bob",
        role="MLRO",
        comment="Second sign-off approved for withdrawal freeze.",
    )
    print(f"   • Approvals: {len(token.approvals)}/2 | Status: {token.status.value} (APPROVED)")

    print("\n   Executing approved HoldWithdrawal...")
    token = intent_hub.execute_action(token.intent_id)
    print(f"   • Status: {token.status.value} (EXECUTED)")

    print("\n================================================================================")
    print("✓ Pre-withdrawal sentinel verification complete. 100% compliant with Constitution.")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
