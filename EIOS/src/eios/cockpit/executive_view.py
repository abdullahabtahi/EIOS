"""What the executive screen shows, shaped from an executive read model (spec 034).

Both planes satisfy `ExecutiveReadModel`, so this never asks which one it has; the plane's origin travels with the
payload and the screen says where the numbers came from.
"""

from __future__ import annotations

from typing import Any

from eios.cockpit.executive_readmodel import ExecutiveReadModel

_RATES = {"competitor_payout_rate": "{:.3f}", "partner_churn_rate": "{:.1%}"}


def format_metric(metric_id: str, value: float) -> str:
    """A metric's value as the cockpit prints it: dollars, a rate, or a plain number."""
    if metric_id in _RATES:
        return _RATES[metric_id].format(value)
    return f"${value:,.0f}" if "usd" in metric_id else f"{value:,.1f}"


def board_payload(svc: ExecutiveReadModel, data_origin: str) -> dict[str, Any]:
    """The executive board in one response: briefing, forecast with its measured interval, causal graph, shocks."""
    briefing = svc.get_morning_briefing()
    return {
        "data_origin": data_origin,
        "as_of": briefing.generated_at.isoformat(),
        "briefing": briefing.to_contract_dict(),
        "figures": {
            h.horizon_name: format_metric(h.primary_metric_id, h.observed_value)
            for h in briefing.horizons
        },
        "forecast": svc.get_forecast("net_revenue_usd").model_dump(),
        "dag": svc.get_causal_dag().to_contract_dict(),
        "shocks": svc.shocks(),
        "stage_requests": svc.stage_requests(),
    }
