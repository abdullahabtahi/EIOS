"""Tests for carrier-NAT hub suppression noise and high-degree IP collision (SC-006, FR-023)."""

from eios.foundry.noise.hard_negatives import CarrierNATHubGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_carrier_nat_hub_suppression_degree():
    """Confirms at least 1 IP is shared by >= 500 unlinked accounts and flagged as a benign hub."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=600)
    hub_gen = CarrierNATHubGenerator(universe=universe, rng=rng)

    hub_edges = hub_gen.generate_hub_edges(target_account_count=500)
    assert len(hub_edges) >= 500

    ip_to_accounts: dict[str, set[str]] = {}
    for edge in hub_edges:
        ip_to_accounts.setdefault(edge["ip_address"], set()).add(edge["client_id"])
        assert edge["is_hub"] is True
        assert edge["tag"] == "BENIGN_HUB"

    # Verify at least 1 IP address is shared by >= 500 unlinked accounts
    hub_ips = [ip for ip, accs in ip_to_accounts.items() if len(accs) >= 500]
    assert len(hub_ips) >= 1, f"Expected at least 1 IP with >= 500 accounts, found {len(hub_ips)}"
