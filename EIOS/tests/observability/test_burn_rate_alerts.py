"""Unit and contract tests for Google SRE multi-window multi-burn-rate alerting policies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from eios.observability.alerts import (
    SREAlertEngine,
    SREAlertSeverity,
    alert_to_contract_dict,
)
from eios.observability.schemas import validate_contract
from eios.observability.slo_catalog import SLICategory
from eios.observability.slo_engine import SLOMonitoringEngine


def test_page_sev1_fires_with_dual_window_confirmation():
    """Verify Page SEV-1 fires when BOTH long window (1h) and short window (5m) burn >= 14.4x."""
    slo_engine = SLOMonitoringEngine()
    alert_engine = SREAlertEngine(slo_engine=slo_engine)
    now = datetime.now(UTC)

    # Ingest sustained rapid burn for INGESTION_FRESHNESS (target 99.0%, allowed error = 1.0%)
    # Burn rate 14.4x means actual error rate = 14.4 * 1% = 14.4%.
    # Ingest 200 events in past 50 mins: ~16.7% error rate -> burn rate ~16.7x (clearly >= 14.4x)
    for i in range(200):
        is_compliant = i % 6 != 0
        slo_engine.record_event(
            sli_name=SLICategory.INGESTION_FRESHNESS,
            observed_value=10.0 if is_compliant else 45.0,
            target_threshold=30.0,
            is_compliant=is_compliant,
            correlation_id=f"alert-sustained-{i}",
            service_name="ingestion_pipeline",
            timestamp=now
            - timedelta(seconds=i * 15),  # within past 50 minutes, and also within past 5 minutes
        )

    alerts = alert_engine.evaluate_alerts(reference_time=now)
    sev1_alerts = [a for a in alerts if a.severity == SREAlertSeverity.PAGE_CRITICAL_SEV1]
    assert len(sev1_alerts) >= 1
    sev1 = sev1_alerts[0]
    assert sev1.sli_name == SLICategory.INGESTION_FRESHNESS
    assert sev1.burn_rate >= 14.4
    assert "Page SEV-1" in sev1.policy_name or "14.4x" in sev1.message


def test_page_sev1_suppressed_if_short_window_healthy():
    """Verify Page SEV-1 is SUPPRESSED if 1h window has errors but 5m short window is healthy."""
    slo_engine = SLOMonitoringEngine()
    alert_engine = SREAlertEngine(slo_engine=slo_engine)
    now = datetime.now(UTC)

    # Ingest heavy errors between 40 and 20 minutes ago
    for i in range(100):
        slo_engine.record_event(
            sli_name=SLICategory.INGESTION_FRESHNESS,
            observed_value=50.0,
            target_threshold=30.0,
            is_compliant=False,
            correlation_id=f"alert-old-{i}",
            service_name="ingestion_pipeline",
            timestamp=now - timedelta(minutes=25 + (i % 15)),
        )

    # Ingest 100% compliant events in the last 5 minutes (incident already mitigated)
    for i in range(50):
        slo_engine.record_event(
            sli_name=SLICategory.INGESTION_FRESHNESS,
            observed_value=12.0,
            target_threshold=30.0,
            is_compliant=True,
            correlation_id=f"alert-recent-{i}",
            service_name="ingestion_pipeline",
            timestamp=now - timedelta(seconds=i * 5),
        )

    alerts = alert_engine.evaluate_alerts(reference_time=now)
    # The short-window confirmation suppresses the SEV-1 Pager!
    sev1_alerts = [a for a in alerts if a.severity == SREAlertSeverity.PAGE_CRITICAL_SEV1]
    assert len(sev1_alerts) == 0


def test_immediate_sev1_on_ledger_mismatch():
    """Verify immediate Page SEV-1 alert on cryptographic ledger sequence mismatch."""
    alert_engine = SREAlertEngine()
    now = datetime.now(UTC)

    alert = alert_engine.emit_ledger_integrity_alert(
        service_name="ledger_sequencer",
        expected_seq=1045,
        actual_seq=1047,
        previous_hash="a1b2c3",
        current_hash="x9y8z7",
        timestamp=now,
    )

    assert alert.severity == SREAlertSeverity.PAGE_CRITICAL_SEV1
    assert "ledger_sequencer" in alert.service_name
    assert "Ledger cryptographic mismatch" in alert.message
    assert alert.is_active is True


def test_sev2_on_dlq_backlog_breach():
    """Verify Ticket SEV-2 alert when Dead-Letter Queue exceeds threshold."""
    alert_engine = SREAlertEngine()
    now = datetime.now(UTC)

    alert = alert_engine.emit_dlq_backlog_alert(
        service_name="omcp_router",
        dlq_depth=145,
        threshold=100,
        timestamp=now,
    )

    assert alert.severity == SREAlertSeverity.TICKET_HIGH_SEV2
    assert "DLQ backlog breach" in alert.message
    assert alert.is_active is True


def test_alert_contract_schema_compliance():
    """Verify SREAlertEvent payload conforms to sre-alert-event.schema.json."""
    alert_engine = SREAlertEngine()
    now = datetime.now(UTC)

    alert = alert_engine.emit_dlq_backlog_alert(
        service_name="omcp_router",
        dlq_depth=120,
        threshold=100,
        timestamp=now,
    )

    payload = alert_to_contract_dict(alert)
    assert validate_contract(payload, "sre-alert-event.schema.json") is True


def test_ticket_sev3_burn_rate_and_resolve():
    """Verify Ticket SEV-3 policy triggers on 1.0x burn over 24h + 2h and can be resolved."""
    slo_engine = SLOMonitoringEngine()
    alert_engine = SREAlertEngine(slo_engine=slo_engine)
    now = datetime.now(UTC)

    # Ingest baseline 1.5x burn for AGENT_TURN_FIRST_TOKEN (target 99.0%, allowed failure 1.0%)
    # 1.5% failures across 24h and 2h
    for i in range(100):
        is_compliant = i != 0 and i != 50
        slo_engine.record_event(
            sli_name=SLICategory.AGENT_TURN_FIRST_TOKEN,
            observed_value=2.0 if is_compliant else 4.0,
            target_threshold=3.0,
            is_compliant=is_compliant,
            correlation_id=f"c-sev3-{i}",
            service_name="agent_coordinator",
            timestamp=now - timedelta(minutes=i * 10),
        )

    alerts = alert_engine.evaluate_alerts(reference_time=now)
    sev3_alerts = [a for a in alerts if a.severity == SREAlertSeverity.TICKET_MEDIUM_SEV3]
    assert len(sev3_alerts) >= 1
    alert_id = sev3_alerts[0].alert_id

    # Active alerts includes this alert
    active = alert_engine.get_active_alerts()
    assert any(a.alert_id == alert_id for a in active)

    # Resolve alert
    alert_engine.resolve_alert(alert_id)
    active_after = alert_engine.get_active_alerts()
    assert not any(a.alert_id == alert_id for a in active_after)
