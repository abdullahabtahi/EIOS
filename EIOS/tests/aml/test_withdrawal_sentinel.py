"""Unit and latency benchmark tests for Pre-Withdrawal Sentinel (US2 / P1).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4, §6.1
- specs/010-client-aml/spec.md (User Story 2, SC-004)
- .specify/memory/constitution.md (Principles I, II)
"""

import time
import pytest
from eios.aml.models import WithdrawalDisposition
from eios.aml.withdrawal_sentinel import WithdrawalSentinel
from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.intent_hub import ActionIntentHub, ActionStatus


def test_withdrawal_sentinel_latency_and_decision() -> None:
    """Benchmark evaluation latency and decision logic (< 2.0s SLO)."""
    hot_state = HotStateEngine()
    intent_hub = ActionIntentHub()
    sentinel = WithdrawalSentinel(hot_state=hot_state, intent_hub=intent_hub)

    # 1. Evaluate clean customer withdrawal
    t0 = time.perf_counter()
    clean_assessment = sentinel.evaluate_withdrawal(
        withdrawal_id="WDL-CLEAN-01",
        client_id="C-CLEAN-01",
        amount_usd=250.0,
        recent_alert_score=0.15,
        hours_since_deposit=120.0,
        market_risk_pct=0.25,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert clean_assessment.recommendation == WithdrawalDisposition.ALLOW
    assert clean_assessment.risk_score < 0.40
    assert clean_assessment.intent_id is None
    assert latency_ms < 2000.0, f"Latency {latency_ms:.2f}ms exceeded 2000ms SLO"

    # 2. Evaluate high-risk laundering withdrawal
    t0 = time.perf_counter()
    risk_assessment = sentinel.evaluate_withdrawal(
        withdrawal_id="WDL-LAUNDER-01",
        client_id="C-AML-ROUNDTRIP-01",
        amount_usd=499.50,
        recent_alert_score=0.92,
        hours_since_deposit=2.5,
        market_risk_pct=0.0001,
        hours_since_kyc=18.0,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    assert risk_assessment.recommendation == WithdrawalDisposition.PROPOSE_HOLD
    assert risk_assessment.risk_score >= 0.80
    assert risk_assessment.intent_id is not None
    assert latency_ms < 2000.0, f"Latency {latency_ms:.2f}ms exceeded 2000ms SLO"


def test_withdrawal_sentinel_emits_kms_signed_proposal_requiring_human_approval() -> None:
    """Verify emitted proposal is KMS-signed, PENDING, and not auto-executed (Principle II)."""
    hot_state = HotStateEngine()
    intent_hub = ActionIntentHub()
    sentinel = WithdrawalSentinel(hot_state=hot_state, intent_hub=intent_hub)

    assessment = sentinel.evaluate_withdrawal(
        withdrawal_id="WDL-HOLD-99",
        client_id="C-SUSPECT-99",
        amount_usd=3000.0,
        recent_alert_score=0.88,
        hours_since_deposit=1.0,
        market_risk_pct=0.0001,
        hours_since_kyc=24.0,
    )

    assert assessment.intent_id is not None
    token = intent_hub.get_status(assessment.intent_id)
    assert token is not None
    assert token.action_type == "HoldWithdrawal"
    assert token.status == ActionStatus.PENDING
    assert token.signature is not None
    assert token.requires_dual_approval is True  # amount > $2,500


def test_withdrawal_sentinel_persists_to_hot_state() -> None:
    """Verify persistence into DuckDB aml_withdrawal_assessments."""
    hot_state = HotStateEngine()
    intent_hub = ActionIntentHub()
    sentinel = WithdrawalSentinel(hot_state=hot_state, intent_hub=intent_hub)

    assessment = sentinel.evaluate_withdrawal(
        withdrawal_id="WDL-DB-01",
        client_id="C-DB-01",
        amount_usd=150.0,
        recent_alert_score=0.20,
    )

    cursor = hot_state.get_cursor()
    row = cursor.execute(
        "SELECT withdrawal_id, client_id, recommendation FROM aml_withdrawal_assessments WHERE withdrawal_id = 'WDL-DB-01'"
    ).fetchone()

    assert row is not None
    assert row[0] == "WDL-DB-01"
    assert row[1] == "C-DB-01"
    assert row[2] == "ALLOW"
