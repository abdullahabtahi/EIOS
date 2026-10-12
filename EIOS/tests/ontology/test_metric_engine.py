"""Test DuckDB Vectorized Metric Engine and parameterized compiler (T011)."""

import time

import pytest

from eios.ontology.metrics.engine import (
    InvalidDimensionFilterError,
    MetricEngine,
    MetricQuery,
    MetricResult,
)
from eios.ontology.metrics.registry import MetricDefinition, MetricRegistry


def test_metric_engine_execution_on_hot_state(seeded_hot_state):
    registry = MetricRegistry()
    registry.register(
        MetricDefinition(
            metric_id="net_deposit_volume_usd",
            name="Net Deposit Volume",
            formula="SUM(CASE WHEN txn_type = 'deposit' THEN amount ELSE -amount END)",
            source_products=["transactions_aml"],
            grain=["currency"],
            dimension_filters=["currency", "payment_method_id"],
            owner_role="cfo",
            unit="USD",
            semantic_version="1.0.0",
        )
    )

    engine = MetricEngine(hot_state=seeded_hot_state, registry=registry)
    query = MetricQuery(
        metric_id="net_deposit_volume_usd",
        filters={"currency": "USD"},
        period="last_30d",
    )
    result = engine.execute(query)

    assert isinstance(result, MetricResult)
    assert result.metric_id == "net_deposit_volume_usd"
    assert result.unit == "USD"
    assert result.value > 0.0
    assert result.execution_duration_ms < 50.0  # Well within test bounds


def test_metric_engine_rejects_unwhitelisted_dimension_filter(seeded_hot_state):
    registry = MetricRegistry()
    registry.register(
        MetricDefinition(
            metric_id="safe_metric",
            name="Safe Metric",
            formula="COUNT(*)",
            source_products=["transactions_aml"],
            grain=["currency"],
            dimension_filters=["currency"],  # only currency is allowed
            owner_role="analyst",
            unit="count",
        )
    )
    engine = MetricEngine(hot_state=seeded_hot_state, registry=registry)
    with pytest.raises(InvalidDimensionFilterError):
        engine.execute(
            MetricQuery(
                metric_id="safe_metric",
                filters={"malicious_column' OR 1=1 --": "ATTACK"},
            )
        )


def test_metric_engine_query_latency_sub_10ms(seeded_hot_state):
    registry = MetricRegistry()
    registry.register(
        MetricDefinition(
            metric_id="tx_count",
            name="Transaction Count",
            formula="COUNT(*)",
            source_products=["transactions_aml"],
            grain=["currency"],
            dimension_filters=["currency"],
            owner_role="ops",
            unit="count",
        )
    )
    engine = MetricEngine(hot_state=seeded_hot_state, registry=registry)
    query = MetricQuery(metric_id="tx_count", filters={"currency": "USD"})

    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = engine.execute(query)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    assert p95 < 10.0, f"P95 query latency exceeded 10ms: {p95:.2f}ms"
