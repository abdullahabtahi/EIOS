"""Unit tests for NetworkX 3-layer referral ring mapping and master partner attribution (T014 / US2).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US2, FR-004, FR-005, SC-003)
- specs/009-partner-fraud/research.md §2
"""

import pytest

from eios.fraud.ring_attribution import ReferralRingAttributionEngine


def test_referral_ring_attribution_recovers_master_partner(synthetic_referral_tree: list[dict]) -> None:
    engine = ReferralRingAttributionEngine(hub_degree_threshold=50)
    engine.build_graph(synthetic_referral_tree)

    # Test attribution from leaf node: P-LEAF-01-A1
    attribution = engine.attribute_partner_ring("P-LEAF-01-A1")

    assert attribution.master_partner_id == "P-MASTER-01"
    assert attribution.hierarchy_depth == 3
    assert attribution.total_affiliated_partners == 5
    assert attribution.total_referred_clients == 100
    assert attribution.total_ring_commission_usd == 29900.0

    # Verify nodes present
    master_node = next((n for n in attribution.nodes if n.partner_id == "P-MASTER-01"), None)
    assert master_node is not None
    assert master_node.is_root_master is True
    assert master_node.tier_level == 1


def test_hub_suppression_prevents_false_flagging_of_legitimate_brokers(synthetic_referral_tree: list[dict]) -> None:
    """Hub suppression ensures high-degree legitimate brokers don't get inflated risk scores."""
    engine = ReferralRingAttributionEngine(hub_degree_threshold=50)
    engine.build_graph(synthetic_referral_tree)

    # Legitimate hub has 80 sub-affiliates
    attribution = engine.attribute_partner_ring("P-LEGIT-HUB")
    assert attribution.master_partner_id == "P-LEGIT-HUB"
    # Hub penalty applied to risk score
    assert attribution.ring_risk_score < 0.30


def test_cycle_detection_breaks_loops_safely() -> None:
    """Circular referral links (e.g. A -> B -> A) must be detected and broken."""
    cyclic_tree = [
        {"partner_id": "P-LOOP-A", "parent_partner_id": "P-LOOP-B", "tier_level": 1, "direct_referred_clients": 10, "direct_commission_usd": 1000.0, "sub_affiliate_count": 1, "is_root_master": True},
        {"partner_id": "P-LOOP-B", "parent_partner_id": "P-LOOP-A", "tier_level": 2, "direct_referred_clients": 5, "direct_commission_usd": 500.0, "sub_affiliate_count": 1, "is_root_master": False},
    ]

    engine = ReferralRingAttributionEngine()
    engine.build_graph(cyclic_tree)

    attribution = engine.attribute_partner_ring("P-LOOP-B")
    # Must not hang or raise infinite recursion
    assert attribution.master_partner_id in ["P-LOOP-A", "P-LOOP-B"]
    assert attribution.hierarchy_depth <= 3
