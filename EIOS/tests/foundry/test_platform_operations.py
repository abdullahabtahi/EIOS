"""Tests for platform operations telemetry and planted latency shock (FR-045)."""

import pytest
from eios.foundry.contracts import ContractValidator, OperationalMetricRecord
from eios.foundry.generators.operational import OperationalDataGenerator
from eios.foundry.rng import DeterministicRNG


def test_platform_operations_and_planted_shock():
    """Confirms operational metrics telemetry passes schema and contains exactly 1 planted incident shock."""
    rng = DeterministicRNG(master_seed=42)
    ops_gen = OperationalDataGenerator(rng=rng)

    metrics = ops_gen.generate_metrics(hours=48)
    assert len(metrics) >= 48

    validator = ContractValidator(OperationalMetricRecord)
    validated = validator.validate_batch(metrics)
    assert len(validated) == len(metrics)

    # Check for planted shock
    incident_metrics = [m for m in validated if m.is_incident_active]
    assert len(incident_metrics) > 0, "Must contain active incident periods"

    # Confirm latency during incident spikes dramatically over baseline (e.g. > 1000ms vs normal < 150ms)
    incident_latencies = [m.p95_latency_ms for m in incident_metrics]
    normal_latencies = [m.p95_latency_ms for m in validated if not m.is_incident_active]

    assert max(incident_latencies) >= 1000.0, "Planted shock must exhibit spike latency"
    assert sum(normal_latencies) / len(normal_latencies) < 250.0
