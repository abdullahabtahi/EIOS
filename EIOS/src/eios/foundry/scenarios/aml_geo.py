"""Geography of the seeded AML world: where each login came from and where each payment instrument is from.

Country level only (policy P-2). One row per transaction in `geo_flows`, keyed by `txn_id`, so the transaction
contract and the warehouse tables stay exactly as they are; each row's login country is the country of the session the
transaction was made in (`aml_sessions`). Planted stories, with their truth kept apart for evaluation:

- ``mismatch_malicious``: every mule ring logs in through its own shared VPN exit abroad.
- ``mismatch_benign``: travellers on a trip and privacy-minded VPN users also log in from abroad. A lens that flags
  every mismatch will flag them too; that is the false-positive cost the evaluation measures.
- ``risky_clients``: structuring accounts whose money moves through Myanmar and wash accounts routed through the
  British Virgin Islands, the planted high-risk corridors.

A separate random stream keeps every other part of the world byte-identical.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_sessions import SessionRoles, build_sessions

GEO_COLUMNS = ("txn_id", "client_id", "ip_country", "instrument_country")

REGIONAL_HUBS = ("SG", "AE")
STRUCTURING_HOP = "MM"  # FATF call for action in the reference layer
WASH_HOP = "VG"  # offshore centre and FATF increased monitoring in the reference layer

_BASE_FOREIGN_INSTRUMENT = 0.08
_PLANTED_HOP = 0.9
_DEPOSIT = "DEPOSIT"


@dataclass(frozen=True)
class GeoTruth:
    """What was planted. Evaluation only; no engine reads it."""

    mismatch_malicious: frozenset[str]
    mismatch_benign: frozenset[str]
    risky_clients: frozenset[str]
    risky_corridors: frozenset[tuple[str, str]]
    ring_exits: Mapping[str, frozenset[str]] = field(
        default_factory=dict
    )  # VPN exit gateway -> ring members
    travellers: frozenset[str] = frozenset()
    privacy_vpn: frozenset[str] = frozenset()


def _other_country(rng: np.random.Generator, home: np.ndarray, pool: tuple[str, ...]) -> np.ndarray:
    """A country from `pool` that differs from `home`, element by element."""
    options = np.array(sorted(pool))
    idx = rng.integers(0, len(options), size=len(home))
    idx = np.where(options[idx] == home, (idx + 1) % len(options), idx)
    return options[idx]


def _window(config: AmlWorldConfig) -> tuple[pd.Timestamp, pd.Timestamp]:
    end = pd.Timestamp(config.as_of)
    end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
    return end - pd.Timedelta(days=config.window_days), end


@dataclass(frozen=True)
class GeoRoles:
    """Who plays which part in the geography: the world's rings, carrier-NAT groups and risky-corridor accounts."""

    rings: tuple[tuple[str, ...], ...]
    cgnat: tuple[tuple[str, ...], ...]
    structuring: Collection[str]
    wash: Collection[str]


def build_geo(
    config: AmlWorldConfig,
    clients: pd.DataFrame,
    transactions: pd.DataFrame,
    roles: GeoRoles,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, GeoTruth]:
    """The geo flows for every transaction, the login sessions, and the truth of what was planted."""
    rings = roles.rings
    risky = {
        **dict.fromkeys(roles.structuring, STRUCTURING_HOP),
        **dict.fromkeys(roles.wash, WASH_HOP),
    }
    sessions, planted = build_sessions(
        clients,
        transactions,
        SessionRoles(rings=rings, cgnat=roles.cgnat, protected=set(risky)),
        _window(config),
        rng,
    )
    home = clients.set_index("client_id")["country"]
    kyc = transactions["client_id"].map(home).to_numpy()
    n = len(transactions)
    by_txn = sessions.dropna(subset=["txn_id"]).set_index("txn_id")["ip_country"]
    ip = transactions["txn_id"].map(by_txn).to_numpy()

    instrument = np.where(
        rng.random(n) < _BASE_FOREIGN_INSTRUMENT, _other_country(rng, kyc, REGIONAL_HUBS), kyc
    )
    hop = transactions["client_id"].map(risky)
    on_hop = hop.notna().to_numpy() & (rng.random(n) < _PLANTED_HOP)
    instrument = np.where(on_hop, hop.fillna("").to_numpy(), instrument)

    flows = pd.DataFrame(
        {
            "txn_id": transactions["txn_id"].to_numpy(),
            "client_id": transactions["client_id"].to_numpy(),
            "ip_country": ip,
            "instrument_country": instrument,
        }
    )
    truth = GeoTruth(
        mismatch_malicious=frozenset(c for ring in rings for c in ring),
        mismatch_benign=planted.travellers | planted.privacy_vpn,
        risky_clients=frozenset(risky),
        risky_corridors=_corridor_pairs(transactions, kyc, instrument, set(risky)),
        ring_exits=dict(planted.ring_exits),
        travellers=planted.travellers,
        privacy_vpn=planted.privacy_vpn,
    )
    return flows, sessions, truth


def corridor(kind: str, kyc: str, instrument: str) -> tuple[str, str]:
    """(origin, destination) of a payment: a deposit comes from the instrument's country, a withdrawal goes to it."""
    return (instrument, kyc) if kind == _DEPOSIT else (kyc, instrument)


def _corridor_pairs(
    transactions: pd.DataFrame, kyc: np.ndarray, instrument: np.ndarray, risky: set[str]
) -> frozenset[tuple[str, str]]:
    mask = transactions["client_id"].isin(risky).to_numpy() & np.isin(
        instrument, (STRUCTURING_HOP, WASH_HOP)
    )
    kinds = transactions["transaction_type"].to_numpy()[mask]
    return frozenset(
        corridor(k, a, b) for k, a, b in zip(kinds, kyc[mask], instrument[mask], strict=True)
    )
