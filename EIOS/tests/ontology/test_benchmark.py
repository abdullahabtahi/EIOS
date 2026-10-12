"""Test for Layer 2 benchmark runner (T048/T050)."""

from eios.ontology.benchmark import run_benchmark


def test_run_benchmark():
    results = run_benchmark()
    assert results["graph_rebuild_passed"] is True
    assert results["metric_latency_passed"] is True
    assert results["query_count"] == 500
    assert results["latency_p95_ms"] <= 10.0
    assert results["graph_rebuild_sec"] < 1.5
