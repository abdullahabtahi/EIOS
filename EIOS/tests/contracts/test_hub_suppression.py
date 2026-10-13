"""Tests for Hub Suppression Filter (ADR-008, US4)."""

from eios.ingestion.entity_resolution.coordinator import SCVCoordinator
from eios.ingestion.entity_resolution.deterministic import ClientProfileRecord
from eios.ingestion.entity_resolution.hub_suppression import HubSuppressionFilter


def test_hub_suppression_detects_high_degree_node():
    """Device shared across >= 5 distinct tax IDs is flagged as a hub."""
    hub_filter = HubSuppressionFilter(degree_threshold=5)

    shared_device = "dev_family_ipad_pro"

    # 4 distinct tax IDs using the device
    for i in range(4):
        is_hub = hub_filter.register_association(
            attribute_type="device_id",
            attribute_value=shared_device,
            tax_id=f"TAX_ID_{i:04d}",
        )
        assert is_hub is False
        assert hub_filter.is_shared_context("device_id", shared_device) is False

    # 5th distinct tax ID connects: degree becomes 5 >= 5
    is_hub_5th = hub_filter.register_association(
        attribute_type="device_id",
        attribute_value=shared_device,
        tax_id="TAX_ID_0004",
    )
    assert is_hub_5th is True
    assert hub_filter.is_shared_context("device_id", shared_device) is True


def test_hub_suppression_blocks_false_merges_in_coordinator():
    """Coordinator must NOT merge distinct individuals who only share a hub device/IP."""
    coordinator = SCVCoordinator(hub_degree_threshold=5)

    shared_tablet = "dev_tablet_hub_123"

    # 6 family members sharing a tablet, each with unique tax ID and email
    profiles = [
        ClientProfileRecord(
            account_id=f"ACC_{i}",
            platform="DERIV_TRADER",
            tax_id=f"TAX_FAMILY_{i}",
            email_hash=f"hash_email_{i}",
            phone_hash=f"hash_phone_{i}",
            full_name=f"Family Member {i}",
            device_id=shared_tablet,
        )
        for i in range(6)
    ]

    canonical_ids = [coordinator.resolve_record(p) for p in profiles]

    # All 6 family members must remain distinct canonical entities!
    assert len(set(canonical_ids)) == 6

    # Check that device edge is tagged is_shared_context=True
    assert coordinator.hub_filter.is_shared_context("device_id", shared_tablet) is True
