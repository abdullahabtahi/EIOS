"""Shared-infrastructure edges: the public payment agent, CGNAT gateways, households and families (spec 031 FR-002).

These are the hard negatives of the graph. A public payment agent and a carrier-grade NAT gateway connect hundreds
of unrelated clients, so a detector that does not suppress them merges the world into one ring (RL-4). A household
of two is normal; a family of three sharing a tablet looks like a ring to a naive rule and is not one.
"""

from __future__ import annotations

import numpy as np

from eios.foundry.scenarios.aml_config import PAYMENT_AGENT_HUB, AmlWorldConfig
from eios.foundry.scenarios.aml_planted import Planted
from eios.foundry.scenarios.aml_population import token
from eios.foundry.scenarios.aml_rows import DEVICE, IP_ADDRESS, PAYMENT, edge_row

CGNAT = "CGNAT_GATEWAY"
AGENT_HUB = "PAYMENT_AGENT_HUB"
HOUSEHOLD = "HOUSEHOLD_PAIR"
FAMILY = "FAMILY_TRIPLET"


def agent_hub(ids: tuple[str, ...]) -> Planted:
    """`PA-HUB-007`: one public gateway, degree above the RL-4 limit, shared by unrelated clients."""
    edges = tuple(edge_row(c, PAYMENT_AGENT_HUB, PAYMENT) for c in ids)
    return Planted(edges=edges, tags={c: (AGENT_HUB,) for c in ids})


def cgnat_gateways(groups: tuple[tuple[str, ...], ...]) -> Planted:
    """Each group sits behind one carrier gateway address, marked as shared context."""
    edges = tuple(
        edge_row(c, token("ip", "cgnat", k), IP_ADDRESS, shared_context=True)
        for k, group in enumerate(groups)
        for c in group
    )
    return Planted(edges=edges, tags={c: (CGNAT,) for group in groups for c in group})


def households(groups: tuple[tuple[str, ...], ...], label: str, salt: str) -> Planted:
    """Clients in a group share one device fingerprint."""
    edges = tuple(
        edge_row(c, token("dev", salt, k), DEVICE) for k, group in enumerate(groups) for c in group
    )
    return Planted(edges=edges, tags={c: (label,) for group in groups for c in group})


def split_groups(ids: tuple[str, ...], size: int, count: int) -> tuple[tuple[str, ...], ...]:
    """`count` consecutive groups of `size` ids."""
    return tuple(ids[i * size : (i + 1) * size] for i in range(count))


def cgnat_sizes(config: AmlWorldConfig, rng: np.random.Generator) -> tuple[int, ...]:
    low, high = config.cgnat_degree
    return tuple(int(rng.integers(low, high + 1)) for _ in range(config.n_cgnat_hubs))
