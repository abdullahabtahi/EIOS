"""Unit tests for Identity Clustering & Client Recycling Detection (T024 / US4).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US4, FR-008)
- specs/009-partner-fraud/research.md §4
"""

from datetime import datetime

from eios.fraud.recycling_detector import ClientRecyclingDetector


def test_recycling_detector_clusters_multi_affiliate_promotion_harvesters(
    synthetic_identity_clusters: list[dict],
) -> None:
    detector = ClientRecyclingDetector(min_distinct_partners=2)
    clusters = detector.detect_recycling_clusters(synthetic_identity_clusters)

    # Must detect syndicate token tok_id_cluster_a1b2c3d4e5f60001 across 4 partners
    syn_cluster = next(
        (c for c in clusters if c.identity_cluster_key == "tok_id_cluster_a1b2c3d4e5f60001"), None
    )
    assert syn_cluster is not None
    assert len(syn_cluster.distinct_partner_ids) == 4
    assert syn_cluster.total_promotions_harvested_usd == 3200.0
    assert syn_cluster.syndicate_risk_score >= 0.85

    # Solo token tok_id_cluster_0011223344556677 with 1 partner should not be flagged as a recycling syndicate
    solo_cluster = next(
        (c for c in clusters if c.identity_cluster_key == "tok_id_cluster_0011223344556677"), None
    )
    assert solo_cluster is None


def test_recycling_detector_distinguishes_shared_household_network() -> None:
    """Distinct verified KYC individuals sharing a household IP are not penalized as syndicates."""
    household_records = [
        {
            "identity_cluster_key": "tok_id_cluster_house_998877",
            "linked_client_ids": ["CL-HUSBAND", "CL-WIFE"],
            "distinct_partner_ids": ["P-AFF-1", "P-AFF-2"],
            "total_promotions_harvested_usd": 200.0,
            "first_seen": datetime(2026, 9, 1, 0, 0, 0),
            "last_seen": datetime(2026, 9, 10, 0, 0, 0),
            "is_shared_household_network": True,
            "distinct_verified_kyc_count": 2,
        }
    ]

    detector = ClientRecyclingDetector(min_distinct_partners=2)
    clusters = detector.detect_recycling_clusters(household_records)

    assert len(clusters) == 1
    household_cluster = clusters[0]
    # Risk score should be strictly dampened (< 0.40) due to verified distinct KYC
    assert household_cluster.syndicate_risk_score < 0.40
