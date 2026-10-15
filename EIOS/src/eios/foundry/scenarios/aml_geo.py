"""Geography of the seeded AML world: where each login came from and where each payment instrument is from.

Country level only (policy P-2). One row per transaction in `geo_flows`, keyed by `txn_id`, so the transaction
contract and the warehouse tables stay exactly as they are. Planted stories, with their truth kept apart for evaluation:

- ``mismatch_malicious``: the two story rings log in from one shared foreign gateway country.
- ``mismatch_benign``: ordinary travellers and expats who also log in from abroad. A lens that flags every mismatch
  will flag them too; that is the false-positive cost the evaluation measures.
- ``risky_clients``: structuring accounts whose money moves through Myanmar and wash accounts routed through the
  British Virgin Islands, the planted high-risk corridors.

A separate random stream keeps every other part of the world byte-identical.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

import numpy as np
import pandas as pd

from eios.foundry.scenarios.aml_config import COUNTRIES, AmlWorldConfig

GEO_COLUMNS = ("txn_id", "client_id", "ip_country", "instrument_country")

REGIONAL_HUBS = ("SG", "AE")
STORY_GATEWAYS = ("NG", "AE")  # shared foreign login country of story ring 0 and story ring 1
STRUCTURING_HOP = "MM"  # FATF call for action in the reference layer
WASH_HOP = "VG"  # offshore centre and FATF increased monitoring in the reference layer
N_BENIGN_TRAVELLERS = 60

_BASE_FOREIGN_IP = 0.04
_BASE_FOREIGN_INSTRUMENT = 0.08
_MALICIOUS_FOREIGN_IP = 0.9
_TRAVELLER_FOREIGN_IP = 0.85
_PLANTED_HOP = 0.9
_DEPOSIT = "DEPOSIT"


@dataclass(frozen=True)
class GeoTruth:
    """What was planted. Evaluation only; no engine reads it."""

    mismatch_malicious: frozenset[str]
    mismatch_benign: frozenset[str]
    risky_clients: frozenset[str]
    risky_corridors: frozenset[tuple[str, str]]


def _other_country(rng: np.random.Generator, home: np.ndarray, pool: tuple[str, ...]) -> np.ndarray:
    """A country from `pool` that differs from `home`, element by element."""
    options = np.array(sorted(pool))
    idx = rng.integers(0, len(options), size=len(home))
    idx = np.where(options[idx] == home, (idx + 1) % len(options), idx)
    return options[idx]


def _client_overrides(
    clients: pd.DataFrame,
    story_rings: tuple[tuple[str, ...], ...],
    protected: Collection[str],
    rng: np.random.Generator,
) -> tuple[dict[str, str], frozenset[str]]:
    """The foreign login country per mismatching client, and the benign travellers among them."""
    gateway = {c: STORY_GATEWAYS[i] for i, ring in enumerate(story_rings) for c in ring}
    candidates = sorted(set(clients["client_id"]) - set(gateway) - set(protected))
    travellers = frozenset(
        str(c) for c in rng.choice(candidates, size=N_BENIGN_TRAVELLERS, replace=False)
    )
    home = clients.set_index("client_id")["country"]
    abroad = _other_country(rng, home.loc[sorted(travellers)].to_numpy(), COUNTRIES)
    return {**gateway, **dict(zip(sorted(travellers), abroad, strict=True))}, travellers


def build_geo(
    config: AmlWorldConfig,
    clients: pd.DataFrame,
    transactions: pd.DataFrame,
    *,
    story_rings: tuple[tuple[str, ...], ...],
    structuring: Collection[str],
    wash: Collection[str],
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, GeoTruth]:
    """The geo flows for every transaction and the truth of what was planted."""
    del (
        config
    )  # the world's size is already in the frames; kept so the signature mirrors the other planters
    risky = {**dict.fromkeys(structuring, STRUCTURING_HOP), **dict.fromkeys(wash, WASH_HOP)}
    foreign_login, travellers = _client_overrides(clients, story_rings, risky, rng)
    home = clients.set_index("client_id")["country"]
    kyc = transactions["client_id"].map(home).to_numpy()
    n = len(transactions)

    ip = kyc.copy()
    odd = rng.random(n) < _BASE_FOREIGN_IP
    ip = np.where(odd, _other_country(rng, kyc, COUNTRIES), ip)
    fixed = transactions["client_id"].map(foreign_login)
    strong = fixed.notna().to_numpy()
    p_foreign = np.where(
        transactions["client_id"].isin(travellers), _TRAVELLER_FOREIGN_IP, _MALICIOUS_FOREIGN_IP
    )
    ip = np.where(
        strong & (rng.random(n) < p_foreign), fixed.fillna("").to_numpy(), np.where(strong, kyc, ip)
    )

    instrument = np.where(
        rng.random(n) < _BASE_FOREIGN_INSTRUMENT, _other_country(rng, kyc, REGIONAL_HUBS), kyc
    )
    hop = transactions["client_id"].map(risky)
    planted = hop.notna().to_numpy() & (rng.random(n) < _PLANTED_HOP)
    instrument = np.where(planted, hop.fillna("").to_numpy(), instrument)

    flows = pd.DataFrame(
        {
            "txn_id": transactions["txn_id"].to_numpy(),
            "client_id": transactions["client_id"].to_numpy(),
            "ip_country": ip,
            "instrument_country": instrument,
        }
    )
    pairs = _corridor_pairs(transactions, kyc, instrument, set(risky))
    truth = GeoTruth(
        mismatch_malicious=frozenset(c for ring in story_rings for c in ring),
        mismatch_benign=travellers,
        risky_clients=frozenset(risky),
        risky_corridors=pairs,
    )
    return flows, truth


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
