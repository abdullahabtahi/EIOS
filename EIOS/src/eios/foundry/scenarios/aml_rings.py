"""Planted mule rings (spec 031 FR-002, FR-003).

A ring is a set of accounts that share a private device fingerprint (and, for some rings, a payment token), deposit
in tightly matched bursts and move the money out together. The story ring (`CR84920`, 23 accounts) also sits behind
the public payment agent `PA-HUB-007`, which hub suppression must collapse without merging unrelated clients.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_planted import Planted
from eios.foundry.scenarios.aml_population import token
from eios.foundry.scenarios.aml_rows import (
    DEPOSIT,
    DEVICE,
    PAYMENT,
    WITHDRAWAL,
    edge_row,
    txn_row,
)

MULE = "MULE_RING"
RING_NUMBERS = (14, 22, 31, 47, 58, 63)  # ring 14 is the story ring named in the cockpit
_BURST_JITTER_S = 1.2
_PAYMENT_RINGS = frozenset({0, 2, 4})


def ring_token(kind: str, ring_no: int) -> str:
    return token(kind, "ring", ring_no)


def plant_ring(
    members: tuple[str, ...],
    index: int,
    config: AmlWorldConfig,
    rng: np.random.Generator,
    *,
    partner: str | None = None,
    story_times: tuple[pd.Timestamp, ...] = (),
    own_rows: frozenset[str] = frozenset(),
) -> Planted:
    """One ring: shared tokens, matched deposit bursts, a common exit. `index` 1 is the quiet device-only ring.

    Clients in `own_rows` keep the rows planted for them elsewhere (the story accounts), so none are added here.
    """
    ring_no = RING_NUMBERS[index]
    edges = _ring_edges(members, ring_no, index)
    quiet = index == 1
    parts = [_member(cid, ring_no, config, rng, quiet=quiet, times=story_times) for cid in members]
    overrides = {
        cid: {**p_over, **({"partner_id": partner} if partner else {})}
        for cid, (_, p_over) in zip(members, parts, strict=True)
    }
    txns = tuple(
        r
        for cid, (rows, _) in zip(members, parts, strict=True)
        if cid not in own_rows
        for r in rows
    )
    return Planted(
        txns=txns,
        edges=edges,
        overrides=overrides,
        tags={cid: (MULE,) for cid in members},
        rings={f"RING-{ring_no}": members},
    )


def _ring_edges(
    members: tuple[str, ...], ring_no: int, index: int
) -> tuple[dict[str, object], ...]:
    device = [edge_row(c, ring_token("dev", ring_no), DEVICE) for c in members]
    payment = (
        [edge_row(c, ring_token("pay", ring_no), PAYMENT) for c in members]
        if index in _PAYMENT_RINGS
        else []
    )
    return tuple(device + payment)


def _member(
    cid: str,
    ring_no: int,
    config: AmlWorldConfig,
    rng: np.random.Generator,
    *,
    quiet: bool,
    times: tuple[pd.Timestamp, ...],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    burst = pd.Timestamp(config.as_of - timedelta(hours=float(rng.uniform(14.0, 70.0))))
    kyc = burst - timedelta(hours=float(rng.uniform(20.0, 400.0)))
    income = float(np.round(rng.uniform(250.0, 900.0), -1))
    if quiet:
        rows = _quiet_deposits(cid, burst, kyc, rng)
    else:
        rows = _burst_deposits(cid, ring_no, burst, kyc, rng, times)
    return rows, {"kyc_approved_at": kyc, "declared_monthly_income_usd": income}


def _quiet_deposits(
    cid: str, burst: pd.Timestamp, kyc: pd.Timestamp, rng: np.random.Generator
) -> list[dict[str, object]]:
    """The device-only ring: small deposits spread over days and no quick exit."""
    pay = token("pay", cid)
    count = int(rng.integers(1, 4))
    return [
        txn_row(
            cid,
            DEPOSIT,
            float(np.round(rng.uniform(100, 400), -1)),
            burst - timedelta(hours=float(rng.uniform(0, 200))),
            kyc=kyc,
            asset="CARD",
            payment_token=pay,
        )
        for _ in range(count)
    ]


def _burst_deposits(
    cid: str,
    ring_no: int,
    burst: pd.Timestamp,
    kyc: pd.Timestamp,
    rng: np.random.Generator,
    times: tuple[pd.Timestamp, ...],
) -> list[dict[str, object]]:
    """Equal deposits at near-identical instants, then one exit of nearly all of it to the ring's token."""
    count = len(times) or int(rng.integers(2, 5))
    each = float(np.round(rng.uniform(450.0, 560.0), -1))
    instants = times or tuple(burst + timedelta(minutes=20 * i) for i in range(count))
    pay = ring_token("pay", ring_no)
    deposits = [
        txn_row(
            cid,
            DEPOSIT,
            each,
            t + timedelta(seconds=float(rng.uniform(0, _BURST_JITTER_S))),
            kyc=kyc,
            asset="USDT",
            payment_token=pay,
        )
        for t in instants
    ]
    exit_at = max(instants) + timedelta(hours=float(rng.uniform(3.0, 20.0)))
    exit_row = txn_row(
        cid,
        WITHDRAWAL,
        each * len(instants) * float(rng.uniform(0.93, 0.99)),
        exit_at,
        kyc=kyc,
        asset="USDT",
        payment_token=pay,
    )
    return [*deposits, exit_row]
