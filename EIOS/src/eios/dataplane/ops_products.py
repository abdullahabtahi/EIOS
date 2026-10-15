"""Profile the data products the worlds supply: rows, completeness, newest event, and contract enforcement (spec 035).

Row counts and null shares are measured over the whole frame. Where the real ingestion pipeline replayed a product,
its contract breach rate decides health; the circuit breaker's own budget is the threshold. Freshness is reported and
not judged: the worlds are batch snapshots cut at the as-of, so the newest event's age reflects how busy the product
is, not how late ingestion was.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from eios.cockpit.operations import DataProductHealthStatus
from eios.contracts.base import DataProductEnum
from eios.dataplane.ops_replay import ReplayOutcome
from eios.ingestion.circuit_breaker import IngestionCircuitBreaker
from eios.ingestion.dq import FRESHNESS_SLAS

SCHEMA_VERSION = "v1.0.0"
MIN_COMPLETENESS = 0.995  # the fixture board's own threshold for a degraded null-check rate
BREACHED_BREACH_RATE = (
    0.05  # [ASSUMPTION] a hundred times the circuit breaker's budget is a breached contract
)
BREACH_BUDGET = IngestionCircuitBreaker().breach_rate_threshold


@dataclass(frozen=True)
class ProductProfile:
    product: DataProductEnum
    rows: int
    completeness: float  # share of cells that are not null
    newest_event: datetime
    newest_event_age_seconds: float
    status: DataProductHealthStatus
    contract_validated: bool
    breach_rate: float | None
    quarantined: int

    def to_contract_dict(self) -> dict[str, Any]:
        return {
            "product_name": self.product.value,
            "contract_schema_version": SCHEMA_VERSION,
            "row_count": self.rows,
            "null_check_pass_rate": round(self.completeness, 4),
            "last_ingestion_timestamp": self.newest_event.isoformat(),
            "freshness_sla_seconds": int(FRESHNESS_SLAS[self.product]),
            "status": self.status.value,
            "is_degraded": self.status is not DataProductHealthStatus.HEALTHY,
            # Engine-plane additions, outside the fixture contract:
            "newest_event_age_seconds": round(self.newest_event_age_seconds, 1),
            "freshness_judged": False,
            "contract_validated": self.contract_validated,
            "contract_breach_rate": None
            if self.breach_rate is None
            else round(self.breach_rate, 5),
            "quarantined_records": self.quarantined,
        }


def _utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def _completeness(frame: pd.DataFrame, optional: frozenset[str]) -> float:
    """Share of required cells that are filled: a column the contract allows to be empty is not a quality failure."""
    required = frame.drop(columns=[c for c in optional if c in frame.columns])
    cells = required.size
    return 1.0 if cells == 0 else float(1.0 - required.isna().sum().sum() / cells)


def _newest(frame: pd.DataFrame, column: str | None, as_of: datetime) -> datetime:
    """The newest event at or before the cut; a product with no event time is as fresh as the cut itself."""
    if column is None:
        return as_of
    times = _utc(frame[column])
    seen = times[times <= pd.Timestamp(as_of)]
    return as_of if seen.empty else seen.max().to_pydatetime()


def _status(completeness: float, breach_rate: float | None) -> DataProductHealthStatus:
    if breach_rate is not None and breach_rate > BREACHED_BREACH_RATE:
        return DataProductHealthStatus.BREACHED
    if completeness < MIN_COMPLETENESS or (breach_rate is not None and breach_rate > BREACH_BUDGET):
        return DataProductHealthStatus.DEGRADED
    return DataProductHealthStatus.HEALTHY


def profile(
    product: DataProductEnum,
    frame: pd.DataFrame,
    time_column: str | None,
    as_of: datetime,
    replay: ReplayOutcome | None = None,
    optional: frozenset[str] = frozenset(),
) -> ProductProfile:
    done = _completeness(frame, optional)
    rate = replay.breach_rate if replay else None
    newest = _newest(frame, time_column, as_of if as_of.tzinfo else as_of.replace(tzinfo=UTC))
    return ProductProfile(
        product=product,
        rows=len(frame),
        completeness=done,
        newest_event=newest,
        newest_event_age_seconds=max((as_of - newest).total_seconds(), 0.0),
        status=_status(done, rate),
        contract_validated=replay is not None,
        breach_rate=rate,
        quarantined=len(replay.dlq) if replay else 0,
    )
