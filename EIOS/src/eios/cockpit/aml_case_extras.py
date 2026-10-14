"""What surrounds a case's dossier on the AML screen: evidence strip, SAR panel, trade-off and stage requests (spec 031).

Every value is read from the engine for the selected account. Where the platform has nothing to say (no pending
withdrawal, no statutory text yet) the field is absent, never filled with a sample.
"""

from __future__ import annotations

from typing import Any

from eios.cockpit.aml_metric import metric as _metric
from eios.dataplane.aml_service import EngineAMLService
from eios.ontology.omcp.port.proposals import hold_stage_request

_ALERT_MULTIPLE = 3.0  # deposits at or above this multiple of declared income read as an alert
_ALERT_WITHDRAWN = 0.9
_NEAR_ZERO_PNL_USD = 0.05  # the wash typology: trades netting to within five cents
HOLD_REASON = "Held for review by the investigator"
FILE_SAR_ACTION = "FileSARDraft"
STATUTORY_NOTE = "Statutory citations attach once regulation retrieval is connected."


def evidence_strip(engine: EngineAMLService, entity_id: str) -> dict[str, Any]:
    view = engine.get_case_view(entity_id)
    ev, case = view["evidence"], view["case"]
    dossier = engine.get_entity_dossier(entity_id)
    income = max(ev["declared_monthly_income_usd"], 1.0)
    volume = ev["realized_deposit_volume_30d_usd"]
    multiple = volume / income
    ring = view["ring"]
    as_of = engine.as_of.isoformat()
    return {
        "title": f"One-Screen Evidence Dossier: {entity_id} ({dossier.kyc.country_of_residence})",
        "severity": case["tier"] if case else "NONE",
        "score": round(case["risk_score"] / 100.0, 2) if case else None,
        "tiles": [
            _tile(
                "30-day deposits",
                f"${volume:,.0f}",
                f"{multiple:.1f}x declared income",
                multiple >= _ALERT_MULTIPLE,
            ),
            _tile(
                "Withdrawn",
                f"{ev['withdrawn_share']:.0%}",
                "of deposits left the account",
                ev["withdrawn_share"] >= _ALERT_WITHDRAWN,
            ),
            _trading_tile(ev, volume),
            _network_tile(ring),
        ],
        "metrics": [
            _metric("realized_deposit_volume_30d_usd", f"${volume:,.0f}", volume, as_of),
            _metric("discrepancy_multiplier", f"{multiple:.1f}x", round(multiple, 1), as_of),
        ],
    }


def _tile(label: str, value: str, caption: str, alert: bool) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "caption": caption,
        "tone": "alert" if alert else "neutral",
    }


def _trading_tile(ev: dict[str, float], volume: float) -> dict[str, Any]:
    if ev["trade_count"] <= 0:
        return _tile("Trading", "None", "no trades in the window", False)
    pnl = ev["net_trading_pnl_usd"]
    near_zero = abs(pnl) <= _NEAR_ZERO_PNL_USD
    return _tile(
        "Net trading P&L",
        f"${pnl:+,.2f}",
        f"{int(ev['trade_count'])} trades vs ${volume:,.0f} deposited",
        near_zero,
    )


def _network_tile(ring: dict[str, Any] | None) -> dict[str, Any]:
    if ring is None:
        return _tile("Network", "No ring", "no shared device or payment link", False)
    return _tile("Network", f"{ring['size']} accounts", "share a device fingerprint", True)


def sar_panel(engine: EngineAMLService, entity_id: str) -> dict[str, Any]:
    """The SAR composer's draft, in the browser's shape, from the engine's own narrative."""
    sar = engine.compose_sar_draft(entity_id=entity_id)
    view = engine.get_case_view(entity_id)
    ev, case = view["evidence"], view["case"]
    return {
        "caseId": sar.case_id,
        "subjectName": f"Account {entity_id}",
        "subjectAccountId": entity_id,
        "suspiciousActivityType": (case["typology"] if case else "NONE").replace("_", " ").title(),
        "summaryNarrative": sar.narrative_summary,
        "transactionHistorySummary": _history(engine, entity_id, ev),
        "totalTurnover": ev["realized_deposit_volume_30d_usd"],
        "statutoryCitations": list(sar.statutory_citations),
        "statutoryNote": None if sar.statutory_citations else STATUTORY_NOTE,
        "generatedTimestamp": sar.created_at.isoformat(),
        "status": "DRAFT",
    }


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _history(engine: EngineAMLService, entity_id: str, ev: dict[str, float]) -> str:
    tx = engine.snapshot.world.transactions
    mine = tx[tx["client_id"] == entity_id]
    deposits = int((mine["transaction_type"] == "DEPOSIT").sum())
    withdrawals = int((mine["transaction_type"] == "WITHDRAWAL").sum())
    return (
        f"{_plural(deposits, 'deposit')} and {_plural(withdrawals, 'withdrawal')} in 30 days; "
        f"{_plural(int(ev['trade_count']), 'trade')}, net P&L ${ev['net_trading_pnl_usd']:+,.2f}."
    )


def trade_offs(engine: EngineAMLService, entity_id: str) -> list[dict[str, Any]]:
    """One countermeasure the account supports: hold its pending withdrawal. None when nothing is pending."""
    pending = engine.get_pending_withdrawal(entity_id)
    if pending is None:
        return []
    score = engine.get_alert_score(entity_id)
    return [
        {
            "proposedAction": f"Hold pending withdrawal {pending.withdrawal_id}",
            "projectedReturn": f"${pending.amount_usd:,.0f} stays in the account until review",
            "projectedRisk": "a second approver is required",
            "confidenceScore": round((score or 0) / 100.0, 2),
            "downsideSensitivity": "if the alert is a false positive the customer's withdrawal is delayed; no funds move",
            "evidenceCitations": ["composite_risk_score", "pending_withdrawal_usd"],
            "stageRequest": hold_stage_request(entity_id, pending.withdrawal_id, HOLD_REASON),
        }
    ]


def case_actions(engine: EngineAMLService, entity_id: str) -> dict[str, Any]:
    """Stage requests the hub understands for this account; a missing one means the action does not apply."""
    pending = engine.get_pending_withdrawal(entity_id)
    sar = engine.compose_sar_draft(entity_id=entity_id)
    return {
        "hold": hold_stage_request(entity_id, pending.withdrawal_id, HOLD_REASON)
        if pending
        else None,
        "file_sar": {
            "action_type": FILE_SAR_ACTION,
            "target_entity_id": entity_id,
            "severity": "MEDIUM",
            "requires_four_eyes": True,
            "metadata": {"case_id": sar.case_id, "template_id": sar.regulator_template_id},
        },
    }
