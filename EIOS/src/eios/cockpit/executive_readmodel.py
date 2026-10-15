"""What the tool port and the workstation routes need from an executive read model (spec 034).

Two planes satisfy it: `ExecutiveCockpitService` (hand-written fixtures) and the engine-backed service over the
seeded firm world, which fits its causal graph and forecast from data.
"""

from datetime import datetime
from typing import Any, Protocol

from eios.cockpit.executive import CausalDAGGraph, ForecastView, MorningBriefingDossier
from eios.cockpit.provenance import ProvenanceResolver


class ExecutiveReadModel(Protocol):
    provenance_resolver: ProvenanceResolver

    def get_morning_briefing(self, as_of: datetime | None = None) -> MorningBriefingDossier: ...

    def get_causal_dag(self) -> CausalDAGGraph: ...

    def get_forecast(self, metric_id: str) -> ForecastView: ...

    def shock_path(self, shock_param: str) -> tuple[tuple[str, str], ...]: ...

    def simulate_what_if_shock(self, shock_param: str, magnitude_pct: float) -> dict[str, Any]: ...

    def current_net_revenue(self) -> float:
        """Net revenue as of now: what the portfolio metric `net_revenue_usd` reports."""
        ...

    def shocks(self) -> list[dict[str, Any]]:
        """The shocks the what-if accepts: id, label, and the size of one unit of magnitude."""
        ...

    def stage_requests(self) -> dict[str, dict[str, Any]]:
        """Stage requests for the briefing's opportunities, by opportunity id; empty where none can be staged."""
        ...
