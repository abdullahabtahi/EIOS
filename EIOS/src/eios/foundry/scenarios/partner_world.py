"""The seeded partner world: roster, daily behaviour, messages, commissions, trades and the truth (spec 032).

`build_partner_world` is a pure function of `PartnerWorldConfig`. Independent random streams per concern keep
the world stable when one part changes. The truth table is for evaluation only and is never read by an engine.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from eios.foundry.rng import RNGManager
from eios.foundry.scenarios.partner_comms import COMMS_COLUMNS, partner_messages
from eios.foundry.scenarios.partner_config import CHURN_DRIVERS, Driver, PartnerWorldConfig
from eios.foundry.scenarios.partner_population import ROSTER_COLUMNS, build_roster
from eios.foundry.scenarios.partner_signals import commissions, partner_days
from eios.foundry.scenarios.partner_trades import PlantedPair, build_trades


@dataclass(frozen=True)
class PartnerTruth:
    """What was planted. Evaluation only."""

    drivers: dict[str, str]
    cohort: frozenset[str]
    pairs: tuple[PlantedPair, ...]

    def churners(self) -> frozenset[str]:
        churn = {d.value for d in CHURN_DRIVERS}
        return frozenset(p for p, d in self.drivers.items() if d in churn)

    def seasonal(self) -> frozenset[str]:
        return frozenset(p for p, d in self.drivers.items() if d == Driver.SEASONAL.value)


@dataclass(frozen=True)
class PartnerWorld:
    config: PartnerWorldConfig
    roster: pd.DataFrame  # one row per partner, without the planted driver
    days: pd.DataFrame  # one row per partner per day
    messages: pd.DataFrame
    commissions: pd.DataFrame
    trades: pd.DataFrame
    truth: PartnerTruth


def build_partner_world(config: PartnerWorldConfig) -> PartnerWorld:
    streams = RNGManager(config.seed)
    roster = build_roster(config, streams.get_generator("partner.roster"))
    behaviour = streams.get_generator("partner.behaviour")
    talk = streams.get_generator("partner.comms")
    days: list[pd.DataFrame] = []
    paid: list[pd.DataFrame] = []
    messages: list[dict[str, object]] = []
    for _, row in roster.iterrows():
        series = partner_days(row, config, behaviour)
        days.append(series)
        paid.append(commissions(series, row, config))
        messages.extend(partner_messages(row, config, talk))
    trades, pairs = build_trades(roster, config, streams.get_generator("partner.trades"))
    truth = PartnerTruth(
        drivers=dict(zip(roster["partner_id"], roster["driver"], strict=True)),
        cohort=frozenset(roster.loc[roster["in_cohort"], "partner_id"]),
        pairs=pairs,
    )
    public = [c for c in ROSTER_COLUMNS if c not in ("driver", "onset_day", "competitor")]
    return PartnerWorld(
        config=config,
        roster=roster[public].reset_index(drop=True),
        days=pd.concat(days, ignore_index=True),
        messages=pd.DataFrame(messages, columns=list(COMMS_COLUMNS)),
        commissions=pd.concat(paid, ignore_index=True),
        trades=trades,
        truth=truth,
    )
