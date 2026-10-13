"""Unit and graph clustering tests for Mule Ring Detector (US4 / P2).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 4, SC-005)
"""

import pandas as pd

from eios.aml.mule_ring_detector import MuleRingDetector
from eios.ingestion.hot_state import HotStateEngine


def test_mule_ring_detector_recovers_ring_and_suppresses_hub(
    synthetic_network_edges: pd.DataFrame,
) -> None:
    """Test recovery of planted mule ring and suppression of high-degree public hub."""
    detector = MuleRingDetector()
    clusters = detector.detect_mule_rings(synthetic_network_edges)

    assert len(clusters) >= 1

    # Find planted mule syndicate
    mule_cluster = None
    for c in clusters:
        if "C-MULE-01" in c.member_client_ids:
            mule_cluster = c
            break

    assert mule_cluster is not None
    assert mule_cluster.is_syndicate is True
    assert mule_cluster.cluster_size == 8
    # Assert all 8 members are recovered
    for i in range(1, 9):
        assert f"C-MULE-{i:02d}" in mule_cluster.member_client_ids

    # Assert tokens
    assert "tok_pay_card_alpha_99" in mule_cluster.shared_payment_tokens
    assert "tok_dev_hw_nexus_42" in mule_cluster.shared_device_tokens

    # Verify public hub suppression: tok_ip_airport_cgnat_hub should be in suppressed_hub_tokens
    assert "tok_ip_airport_cgnat_hub" in detector.suppressed_hubs
    # Verify that the 150 public users are NOT grouped into a 150-person fraud syndicate
    public_syndicates = [
        c for c in clusters if any(m.startswith("C-PUBLIC") for m in c.member_client_ids)
    ]
    assert len(public_syndicates) == 0, (
        "Public Wi-Fi accounts were falsely clustered as syndicates!"
    )


def test_mule_ring_detector_generates_plain_language_explanation(
    synthetic_network_edges: pd.DataFrame,
) -> None:
    """Verify non-technical explanation for compliance officers."""
    detector = MuleRingDetector()
    clusters = detector.detect_mule_rings(synthetic_network_edges)

    mule_cluster = next(c for c in clusters if "C-MULE-01" in c.member_client_ids)
    explanation = mule_cluster.plain_language_explanation

    assert "8 linked accounts" in explanation or "8" in explanation
    assert "payment" in explanation.lower()
    assert "device" in explanation.lower()


def test_mule_ring_detector_persists_to_hot_state(
    synthetic_network_edges: pd.DataFrame,
) -> None:
    """Test DuckDB hot-state persistence into aml_mule_rings."""
    hot_state = HotStateEngine()
    detector = MuleRingDetector(hot_state=hot_state)

    clusters = detector.detect_mule_rings(synthetic_network_edges)
    persisted_count = detector.persist_clusters(clusters)
    assert persisted_count >= 1

    cursor = hot_state.get_cursor()
    row = cursor.execute(
        "SELECT cluster_size, is_syndicate FROM aml_mule_rings WHERE client_id = 'C-MULE-01'"
    ).fetchone()

    assert row is not None
    assert row[0] == 8
    assert row[1] is True
