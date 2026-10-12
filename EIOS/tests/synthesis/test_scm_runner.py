"""Tests for offline SCM runner, cache serialization, and Causal Gate compliance (T009, US1)."""

import json

from eios.synthesis.scm import SCMCache
from eios.synthesis.scm_runner import SCMRunner


def test_scm_runner_fit_and_cache(tmp_path, synthetic_timeseries_data):
    """Verify offline fitting, refutation, and cache serialization."""
    cache_file = tmp_path / "synthesis_scm_cache.json"

    runner = SCMRunner(model_version="v1.2.0-causal")
    manifest = runner.fit_and_cache(
        data=synthetic_timeseries_data,
        cache_path=cache_file,
    )

    assert manifest.active_edge_count == 3
    assert manifest.rejected_placebo_count >= 1
    assert cache_file.exists()

    with open(cache_file, encoding="utf-8") as f:
        data = json.load(f)
    assert data["model_version"] == "v1.2.0-causal"
    assert len(data["edges"]) == 3


def test_scm_cache_deserialization_and_fast_lookup(tmp_path, synthetic_timeseries_data):
    """Verify SCMCache loads from disk and provides sub-millisecond edge lookup."""
    cache_file = tmp_path / "synthesis_scm_cache.json"
    runner = SCMRunner(model_version="v1.2.0-causal")
    runner.fit_and_cache(data=synthetic_timeseries_data, cache_path=cache_file)

    scm_cache = SCMCache.load_from_file(cache_file)
    assert scm_cache.model_version == "v1.2.0-causal"

    edges = scm_cache.get_edges_for_outcome("net_deposit_volume_usd")
    assert len(edges) == 3

    # Check edge attributes
    first_edge = edges[0]
    assert first_edge.source_metric == "competitor_payout_rate"
    assert first_edge.target_metric == "partner_churn_rate"


def test_unverified_edge_emits_honest_refusal(tmp_path, synthetic_timeseries_data):
    """Verify that unverified or failing edges emit mandatory refusal phrase per RL-3."""
    cache_file = tmp_path / "synthesis_scm_cache.json"
    runner = SCMRunner(model_version="v1.2.0-causal")
    runner.fit_and_cache(data=synthetic_timeseries_data, cache_path=cache_file)

    scm_cache = SCMCache.load_from_file(cache_file)

    # Query unverified link: avg_spread_pip -> partner_churn_rate
    verdict, message = scm_cache.verify_causal_assertion(
        source_metric="avg_spread_pip",
        target_metric="partner_churn_rate",
    )
    assert verdict is False
    assert "correlation detected; insufficient evidence for causation." in message
