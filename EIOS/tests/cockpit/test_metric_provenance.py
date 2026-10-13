"""Tests for Deterministic Metric Provenance Resolver and Popovers."""

import time

import pytest

from eios.cockpit.provenance import ProvenanceResolver
from eios.cockpit.schemas import validate_contract


def test_resolve_canonical_metric_provenance():
    resolver = ProvenanceResolver()
    meta = resolver.resolve("net_revenue_usd")

    assert meta.metric_id == "net_revenue_usd"
    assert meta.owner_role == "Chief Financial Officer"
    assert meta.definition_version == "1.4.0"
    assert meta.computation_source == "SemanticRegistry.DuckDB"
    assert meta.is_replayed is False

    contract_dict = meta.to_contract_dict()
    assert validate_contract(contract_dict, "provenance-metadata") is True


def test_resolve_replayed_provenance():
    resolver = ProvenanceResolver()
    meta = resolver.resolve("churn_hazard_probability", is_replayed=True)

    assert meta.metric_id == "churn_hazard_probability"
    assert meta.is_replayed is True

    contract_dict = meta.to_contract_dict()
    assert validate_contract(contract_dict, "provenance-metadata") is True


def test_provenance_sub_50ms_latency_sla():
    resolver = ProvenanceResolver()
    # Warmup
    resolver.resolve("net_revenue_usd")

    latencies = []
    for _ in range(500):
        t0 = time.perf_counter()
        resolver.resolve("net_revenue_usd")
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)  # ms

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]
    # Target SLA: < 50ms (in-memory resolution is typically < 0.1ms)
    assert p95 < 50.0


def test_unregistered_metric_raises():
    resolver = ProvenanceResolver()
    with pytest.raises(KeyError, match="not registered"):
        resolver.resolve("hallucinated_invented_metric_999")
