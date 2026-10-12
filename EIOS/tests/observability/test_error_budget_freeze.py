"""Unit tests for automated release freeze gates and Four-Eyes break-glass authorization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from eios.observability.slo_catalog import SLICategory, SLOTier
from eios.observability.slo_engine import (
    BreakGlassOverrideRequest,
    ErrorBudgetHealth,
    ReleaseGateVerdict,
    SLOMonitoringEngine,
)


def test_tier_1_exhaustion_triggers_release_freeze():
    """Verify Tier 1 budget exhaustion blocks releases, while Tier 2 does not block releases."""
    engine = SLOMonitoringEngine()
    now = datetime.now(timezone.utc)

    # 1. Tier 2 exhaustion (AGENT_TURN_FIRST_TOKEN)
    for i in range(100):
        # 50 failures out of 100 -> budget heavily exhausted
        engine.record_event(
            sli_name=SLICategory.AGENT_TURN_FIRST_TOKEN,
            observed_value=8.0,
            target_threshold=3.0,
            is_compliant=False,
            correlation_id=f"t2-{i}",
            timestamp=now - timedelta(minutes=i),
        )

    t2_status = engine.evaluate_slo(SLICategory.AGENT_TURN_FIRST_TOKEN)
    assert t2_status.status == ErrorBudgetHealth.FEATURE_FREEZE
    assert t2_status.is_frozen is False  # Tier 2 does not freeze releases

    verdict_t2 = engine.evaluate_release_gate(service_name="agent_coordinator")
    assert verdict_t2.is_allowed is True

    # 2. Tier 1 exhaustion (LEDGER_CHAIN_INTEGRITY)
    engine.record_event(
        sli_name=SLICategory.LEDGER_CHAIN_INTEGRITY,
        observed_value=1.0,
        target_threshold=0.0,
        is_compliant=False,
        correlation_id="t1-ledger-gap",
        timestamp=now,
    )

    t1_status = engine.evaluate_slo(SLICategory.LEDGER_CHAIN_INTEGRITY)
    assert t1_status.status == ErrorBudgetHealth.FEATURE_FREEZE
    assert t1_status.is_frozen is True

    verdict_t1 = engine.evaluate_release_gate(service_name="ledger_sequencer")
    assert verdict_t1.is_allowed is False
    assert "FEATURE_FREEZE active" in verdict_t1.reason


def test_four_eyes_break_glass_hotfix_override():
    """Verify Constitution Principle II four-eyes break-glass authorization during freeze."""
    engine = SLOMonitoringEngine()
    now = datetime.now(timezone.utc)

    # Freeze system via Tier 1 breach
    engine.record_event(
        sli_name=SLICategory.PRE_WITHDRAWAL_DECISION,
        observed_value=5.0,
        target_threshold=2.0,
        is_compliant=False,
        correlation_id="pre-w-fail",
        timestamp=now,
    )

    # Standard release blocked
    assert engine.evaluate_release_gate("fraud_engine").is_allowed is False

    # Attempt override with identical approver (single-eye cheat attempt) -> REJECTED
    req_single = BreakGlassOverrideRequest(
        approver_1="lead_sre@enterprise.com",
        approver_2="lead_sre@enterprise.com",
        justification="Emergency hotfix for fraud scoring crash",
        expires_at=now + timedelta(hours=2),
    )
    with pytest.raises(ValueError, match="Two distinct approvers required"):
        engine.authorize_break_glass(req_single)

    # Attempt override with expired timestamp -> REJECTED
    req_expired = BreakGlassOverrideRequest(
        approver_1="lead_sre@enterprise.com",
        approver_2="vp_eng@enterprise.com",
        justification="Late hotfix",
        expires_at=now - timedelta(minutes=5),
    )
    with pytest.raises(ValueError, match="Override expiration must be in the future"):
        engine.authorize_break_glass(req_expired)

    # Valid four-eyes approval -> ACCEPTED
    req_valid = BreakGlassOverrideRequest(
        approver_1="lead_sre@enterprise.com",
        approver_2="vp_eng@enterprise.com",
        justification="Hotfix PR-982 patching memory leak in fraud pre-withdrawal engine",
        expires_at=now + timedelta(hours=2),
    )
    override = engine.authorize_break_glass(req_valid)
    assert override.is_active is True

    # Now release gate allows deployment under active override
    verdict_override = engine.evaluate_release_gate("fraud_engine", override_id=override.override_id)
    assert verdict_override.is_allowed is True
    assert "Four-Eyes break-glass override authorized" in verdict_override.reason
