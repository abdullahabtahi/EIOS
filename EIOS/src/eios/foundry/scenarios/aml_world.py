"""The seeded AML world: clients, transactions, trades, graph edges and the truth about what was planted (spec 031).

`build_aml_world` is a pure function of `AmlWorldConfig`. Independent random streams per concern keep the world
stable when one part changes. The truth table is for evaluation only and is never read by a detector.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import accumulate
from typing import Any

import numpy as np
import pandas as pd

from eios.foundry.rng import RNGManager
from eios.foundry.scenarios import aml_geo, aml_hubs, aml_rings, aml_wash
from eios.foundry.scenarios.aml_behaviour import NORMAL, SCALPER, WEALTHY, client_activity
from eios.foundry.scenarios.aml_config import (
    STORY_DEVICE_RING,
    STORY_IDS,
    STORY_PARTNER,
    STORY_RING_HEAD,
    STORY_WASH,
    AmlWorldConfig,
)
from eios.foundry.scenarios.aml_planted import Planted, merge
from eios.foundry.scenarios.aml_population import build_clients, client_ids
from eios.foundry.scenarios.aml_rows import DEPOSIT, edges_frame, trades_frame, transactions_frame

MALICIOUS_TAGS = frozenset({aml_wash.WASH, aml_wash.STRUCTURING, aml_rings.MULE})
_WEALTHY_INCOME = (15000.0, 40000.0)


@dataclass(frozen=True)
class AmlTruth:
    """What was planted. Evaluation only."""

    tags: dict[str, tuple[str, ...]]
    rings: dict[str, tuple[str, ...]]
    geo: aml_geo.GeoTruth | None = None

    def malicious(self) -> frozenset[str]:
        return frozenset(c for c, found in self.tags.items() if MALICIOUS_TAGS & set(found))


@dataclass(frozen=True)
class AmlWorld:
    config: AmlWorldConfig
    clients: pd.DataFrame
    transactions: pd.DataFrame
    trades: pd.DataFrame
    edges: pd.DataFrame
    truth: AmlTruth
    geo_flows: pd.DataFrame | None = None
    geo_sessions: pd.DataFrame | None = (
        None  # login sessions (aml_sessions.SESSION_COLUMNS); geo only
    )


@dataclass(frozen=True)
class _Roles:
    rings: tuple[tuple[str, ...], ...]
    wash: tuple[str, ...]
    structuring: tuple[str, ...]
    scalpers: tuple[str, ...]
    wealthy: tuple[str, ...]
    households: tuple[tuple[str, ...], ...]
    families: tuple[tuple[str, ...], ...]
    cgnat: tuple[tuple[str, ...], ...]
    agent_hub: tuple[str, ...]

    def special(self) -> frozenset[str]:
        """Clients with scripted behaviour; everyone else behaves normally."""
        rung = {c for ring in self.rings for c in ring}
        return frozenset({*rung, *self.wash, *self.structuring, *self.scalpers, *self.wealthy})


def build_aml_world(config: AmlWorldConfig) -> AmlWorld:
    streams = RNGManager(config.seed)
    population = streams.get_generator("aml.population")
    ids = client_ids(config, population)
    clients = build_clients(config, population, ids)
    roles = _assign_roles(config, ids, streams.get_generator("aml.roles"))
    planted = _plant(config, roles, streams.get_generator("aml.typologies"))
    clients = _apply(clients, planted.overrides)
    clients = _apply(clients, _wealthy_overrides(roles, streams.get_generator("aml.wealthy")))
    behaviour = _behaviour(config, clients, roles, streams.get_generator("aml.behaviour"))
    txns = [*behaviour[0], *planted.txns]
    trades = [*behaviour[1], *planted.trades]
    transactions = transactions_frame(txns)
    geo_flows, geo_sessions, geo_truth = aml_geo.build_geo(
        config,
        clients,
        transactions,
        aml_geo.GeoRoles(
            rings=roles.rings,
            cgnat=roles.cgnat,
            structuring=roles.structuring,
            wash=(*roles.wash, STORY_WASH),
        ),
        streams.get_generator("aml.geo"),
    )
    return AmlWorld(
        config=config,
        clients=clients,
        transactions=transactions,
        trades=trades_frame(trades),
        edges=edges_frame(planted.edges),
        truth=AmlTruth(tags=planted.tags, rings=planted.rings, geo=geo_truth),
        geo_flows=geo_flows,
        geo_sessions=geo_sessions,
    )


def _carve(pool: tuple[str, ...], sizes: tuple[int, ...]) -> tuple[tuple[str, ...], ...]:
    """Consecutive disjoint groups of the given sizes from `pool`."""
    ends = tuple(accumulate(sizes))
    starts = (0, *ends[:-1])
    return tuple(pool[a:b] for a, b in zip(starts, ends, strict=True))


def _assign_roles(config: AmlWorldConfig, ids: tuple[str, ...], rng: np.random.Generator) -> _Roles:
    heads = {0: STORY_RING_HEAD, 1: STORY_DEVICE_RING}
    pool = tuple(str(c) for c in rng.permutation(np.array(ids[len(STORY_IDS) :])))
    ring_extra = tuple(size - (1 if i in heads else 0) for i, size in enumerate(config.ring_sizes))
    sizes = (
        *ring_extra,
        config.n_wash,
        config.n_structuring,
        config.n_scalpers,
        config.n_wealthy,
        *(2 for _ in range(config.n_households)),
        *(3 for _ in range(config.n_family_triplets)),
    )
    groups = _carve(pool, sizes)
    n_rings = len(config.ring_sizes)
    rings = tuple((*((heads[i],) if i in heads else ()), *groups[i]) for i in range(n_rings))
    base = n_rings
    hubs_pool = pool[sum(sizes) :]
    cgnat_sizes = aml_hubs.cgnat_sizes(config, rng)
    cgnat = _carve(hubs_pool, cgnat_sizes)
    remaining = hubs_pool[sum(cgnat_sizes) :]
    extra = max(config.n_hub_agent_clients - len(rings[0]), 0)
    return _Roles(
        rings=rings,
        wash=groups[base],
        structuring=groups[base + 1],
        scalpers=groups[base + 2],
        wealthy=groups[base + 3],
        households=groups[base + 4 : base + 4 + config.n_households],
        families=groups[base + 4 + config.n_households :],
        cgnat=cgnat,
        agent_hub=(*rings[0], *remaining[:extra]),
    )


def _plant(config: AmlWorldConfig, roles: _Roles, rng: np.random.Generator) -> Planted:
    head_story = aml_wash.story_structuring(config)
    head_times = tuple(
        pd.Timestamp(r["timestamp"]) for r in head_story.txns if r["transaction_type"] == DEPOSIT
    )
    own = frozenset({STORY_RING_HEAD})
    rings = [
        aml_rings.plant_ring(
            members,
            i,
            config,
            rng,
            partner=STORY_PARTNER if i == 0 else None,
            story_times=head_times if i == 0 else (),
            own_rows=own if i == 0 else frozenset(),
        )
        for i, members in enumerate(roles.rings)
    ]
    return merge(
        [
            *rings,
            head_story,
            aml_wash.story_wash(config),
            aml_wash.wash_accounts(roles.wash, config, rng),
            aml_wash.structuring_accounts(roles.structuring, config, rng),
            aml_hubs.agent_hub(roles.agent_hub),
            aml_hubs.cgnat_gateways(roles.cgnat),
            aml_hubs.households(roles.households, aml_hubs.HOUSEHOLD, "home"),
            aml_hubs.households(roles.families, aml_hubs.FAMILY, "family"),
        ]
    )


def _wealthy_overrides(roles: _Roles, rng: np.random.Generator) -> dict[str, dict[str, Any]]:
    low, high = _WEALTHY_INCOME
    return {
        cid: {
            "declared_monthly_income_usd": float(np.round(rng.uniform(low, high), -2)),
            "employment_status": "Self-Employed",
        }
        for cid in roles.wealthy
    }


def _apply(clients: pd.DataFrame, overrides: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """A copy of `clients` with the given per-client field overrides applied."""
    frame = clients.copy()
    index = pd.Index(frame["client_id"])
    for cid, fields in overrides.items():
        position = index.get_loc(cid)
        for column, value in fields.items():
            frame.iloc[position, frame.columns.get_loc(column)] = value
    frame["cohort_id"] = frame["country"] + ":" + frame["employment_status"]
    return frame


def _behaviour(
    config: AmlWorldConfig, clients: pd.DataFrame, roles: _Roles, rng: np.random.Generator
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    special = roles.special() | frozenset(STORY_IDS)
    normal = clients[~clients["client_id"].isin(special)]
    pools = (
        (normal, NORMAL),
        (clients[clients["client_id"].isin(roles.scalpers)], SCALPER),
        (clients[clients["client_id"].isin(roles.wealthy)], WEALTHY),
    )
    txns: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    for frame, profile in pools:
        t, tr = client_activity(frame, profile, config, rng)
        txns.extend(t)
        trades.extend(tr)
    return txns, trades
