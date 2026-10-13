"""Tests for multi-silo identity fragmentation and hard negative distributions (FR-011 to FR-014)."""

from eios.foundry.generators.client import ClientDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_silo_projection_and_fragmentation():
    """Verifies internal UUIDv5 maps to MT5, Deriv Trader, and DP2P projections."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=500)
    generator = ClientDataGenerator(universe=universe, rng=rng)

    projections = generator.generate_silo_projections()
    assert len(projections) == 500

    for proj in projections:
        # Internal UUIDv5 person ID
        assert "person_id" in proj
        assert len(proj["person_id"]) == 36  # UUID standard length

        # Deriv Trader CR Account
        assert proj["deriv_trader_cr_id"].startswith("CR")

        # MetaTrader 5 Login ID
        assert isinstance(proj["mt5_login_id"], int)
        assert proj["mt5_login_id"] >= 10000000

        # DP2P Nickname
        assert "dp2p_nickname" in proj
        assert len(proj["dp2p_nickname"]) > 0


def test_shared_device_fingerprints_and_domain_variations():
    """Verifies that ~3% shared device fingerprints (hard negatives) and ~5% domain variations exist."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=1000)
    generator = ClientDataGenerator(universe=universe, rng=rng)

    network_edges = generator.generate_device_network()
    client_360 = generator.generate_client_360()

    # Verify device sharing across distinct client_ids (family context hard negatives)
    device_to_clients: dict[str, set[str]] = {}
    for edge in network_edges:
        device_to_clients.setdefault(edge["device_hash"], set()).add(edge["client_id"])

    shared_devices = {
        dev: clients for dev, clients in device_to_clients.items() if len(clients) > 1
    }
    # 3% targeted shared device fingerprints, in 1000 clients we should have at least 15 shared device pairings
    assert len(shared_devices) >= 15

    # Verify email domain variations / duplicate identities (e.g. gmail vs yahoo or variations for same person)
    # Check domain variation flag or variation rate in universe
    variations = [c for c in client_360 if c.get("has_identity_duplicate_noise")]
    assert len(variations) >= 30  # ~5% of 1000 is ~50
