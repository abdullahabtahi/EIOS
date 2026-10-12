"""Unit and contract tests for Four Golden Signals and OMCP system reliability tool."""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from eios.observability.golden_signals import (
    GoldenSignalsCollector,
    ServiceGoldenSignals,
    golden_signals_to_contract_dict,
)
from eios.observability.schemas import validate_contract
from eios.ontology.omcp.server import OMCPServer
from eios.ingestion.hot_state import HotStateEngine


def test_golden_signals_collection_and_percentiles():
    """Verify Four Golden Signals calculation: throughput, p50/p90/p95/p99 latency, errors, saturation."""
    collector = GoldenSignalsCollector()
    now = datetime.now(timezone.utc)

    # Ingest 100 requests for omcp_server: latencies 10ms..1000ms
    for i in range(1, 101):
        collector.record_request(
            service_name="omcp_server",
            latency_ms=float(i * 10),
            is_error=(i > 95),  # 5% error rate
            timestamp=now,
        )
    collector.set_saturation("omcp_server", saturation_pct=65.0)

    signals = collector.get_golden_signals("omcp_server", reference_time=now)
    assert signals.service_name == "omcp_server"
    assert signals.error_rate_pct == 5.0
    assert signals.saturation_pct == 65.0
    assert signals.is_saturated is False

    # Percentiles: 100 items from 10 to 1000
    # p50 ~ 500, p90 ~ 900, p95 ~ 950, p99 ~ 990
    assert pytest.approx(signals.latency_p50_ms, abs=20) == 500.0
    assert pytest.approx(signals.latency_p90_ms, abs=20) == 900.0
    assert pytest.approx(signals.latency_p95_ms, abs=20) == 950.0
    assert pytest.approx(signals.latency_p99_ms, abs=20) == 990.0

    # Contract schema validation
    payload = golden_signals_to_contract_dict(signals)
    assert validate_contract(payload, "service-golden-signals.schema.json") is True


def test_golden_signals_saturation_warning():
    """Verify is_saturated flag triggers when saturation exceeds 85.0%."""
    collector = GoldenSignalsCollector()
    collector.set_saturation("ledger_sequencer", saturation_pct=88.5)

    signals = collector.get_golden_signals("ledger_sequencer")
    assert signals.saturation_pct == 88.5
    assert signals.is_saturated is True


def test_omcp_tool_get_system_reliability_status():
    """Verify canonical OMCP tool get_system_reliability_status returns unified health."""
    hot_state = HotStateEngine()
    server = OMCPServer(hot_state=hot_state)

    res = server.call_tool("get_system_reliability_status", {})
    assert "overall_health" in res
    assert "error_budgets" in res
    assert "active_alerts" in res
    assert "golden_signals" in res
    assert res["overall_health"] in ["HEALTHY", "WARNING", "FEATURE_FREEZE"]
    assert isinstance(res["error_budgets"], list)
    assert len(res["error_budgets"]) >= 10
