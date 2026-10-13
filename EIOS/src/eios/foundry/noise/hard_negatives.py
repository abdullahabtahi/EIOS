"""Hard negative generators including carrier-NAT hub IP collision (FR-023, SC-006)."""

from __future__ import annotations

from typing import Any

from eios.foundry.rng import RNGManager
from eios.foundry.universe import GlobalEntityUniverse


class CarrierNATHubGenerator:
    """Generates carrier-NAT / campus IP hub collisions for entity resolution and AML suppression."""

    def __init__(self, universe: GlobalEntityUniverse, rng: RNGManager) -> None:
        self.universe = universe
        self.rng = rng
        self._gen = rng.get_generator("hub_suppression")

    def generate_hub_edges(self, target_account_count: int = 500) -> list[dict[str, Any]]:
        """Maps target_account_count accounts to a single shared carrier-NAT hub IP."""
        hub_ip = "100.64.0.1"

        selected_accounts = self.universe.accounts[:target_account_count]
        edges: list[dict[str, Any]] = []

        for idx, account in enumerate(selected_accounts):
            edges.append(
                {
                    "edge_id": f"HUB-{idx:08d}",
                    "client_id": account.client_id,
                    "device_hash": account.client_id + "_dev",
                    "ip_address": hub_ip,
                    "is_hub": True,
                    "tag": "BENIGN_HUB",
                    "timestamp": account.created_at,
                }
            )

        return edges
