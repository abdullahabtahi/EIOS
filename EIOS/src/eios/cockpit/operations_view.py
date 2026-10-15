"""What the operations workstation shows, from the engine-backed operations service (spec 035).

The board's cards are the profiled products and the SLO engine's indicators; the gates are the measured red lines;
the quarantine list is the pipeline's own dead-letter records; the recovery proof is the restore drill that was run.
A figure nothing measured is absent, never zero and never healthy.
"""

from __future__ import annotations

from typing import Any

from eios.cockpit.aml_metric import metric
from eios.dataplane.ops_service import EngineOperationsService

STEWARD = "PlatformOperationsSteward"
ENGINE = "EngineOperationsService"
SEVERITY = {"BREACHED": "CRITICAL", "DEGRADED": "HIGH", "HEALTHY": "LOW"}


def red_line_payload(svc: EngineOperationsService) -> list[dict[str, Any]]:
    return [
        {
            "gate_id": g.gate_id,
            "name": g.name,
            "status": g.status,
            "margin_delta": g.margin,
            "basis": g.basis,
        }
        for g in svc.red_lines()
    ]


def dr_proofs(svc: EngineOperationsService) -> list[dict[str, Any]]:
    d = svc.drill
    return [
        {
            "runbook_id": "RUNBOOK-08",
            "runbook_name": "Warm-start rehydration from the Parquet lakehouse",
            "last_executed": d.ran_at.isoformat(),
            "verification_status": "PASS" if d.verified else "FAIL",
            "kms_keyring_rotation_status": "NOT_ASSESSED",  # a restore drill says nothing about key rotation
            "backup_checkpoint_hash": d.checkpoint_hash,
            "warm_start_cache_state": "WARMED" if d.verified else "COLD",
            "rows_restored": d.rows_restored,
            "rows_exported": d.rows_exported,
            "restore_ms": d.restore_ms,
        }
    ]


def _triage(svc: EngineOperationsService, now_iso: str) -> list[dict[str, Any]]:
    items = [
        {
            "id": f"item_dp_{p['product_name']}",
            "title": f"Data Product {p['product_name']}",
            "subtitle": (
                f"{p['row_count']:,} rows | completeness {p['null_check_pass_rate'] * 100:.2f}% | "
                f"{p['status']}"
                + (
                    f" | {p['quarantined_records']} quarantined"
                    if p.get("quarantined_records")
                    else ""
                )
            ),
            "entity_id": p["product_name"],
            "priority_score": {"BREACHED": 0.95, "DEGRADED": 0.85}.get(p["status"], 0.2),
            "severity": SEVERITY[p["status"]],
            "status": "OPEN" if p["status"] != "HEALTHY" else "RESOLVED",
            "timestamp": now_iso,
        }
        for p in svc.product_cards()
    ]
    return sorted(items, key=lambda i: i["priority_score"], reverse=True)


def _summary(svc: EngineOperationsService) -> str:
    board = svc.get_board_summary()
    bad = board["degraded_products"] + board["breached_products"]
    gates = svc.red_lines()
    passing = sum(1 for g in gates if g.status == "PASS")
    unmeasured = sum(1 for g in gates if g.status == "NOT_MEASURED")
    observed = sum(1 for b in svc.error_budgets() if b["status"] != "NO_DATA")
    return (
        f"{board['healthy_products']} of {board['total_products']} data products are healthy"
        f"{f' and {bad} need attention' if bad else ''}. {passing} of {len(gates)} red lines pass and {unmeasured} are "
        f"not measured here. {observed} of {len(svc.error_budgets())} service objectives were observed by the probes."
    )


def workstation(
    svc: EngineOperationsService, now_iso: str
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    replay, drill = svc.replay, svc.drill
    metrics = [
        metric(
            "contract_enforcement",
            f"{replay.caught} of {replay.planted} planted breaches quarantined",
            float(replay.caught),
            now_iso,
            engine_name=ENGINE,
            steward=STEWARD,
        ),
        metric(
            "restore_drill_rows",
            f"{drill.rows_restored:,} of {drill.rows_exported:,} rows restored",
            float(drill.rows_restored),
            now_iso,
            engine_name=ENGINE,
            steward=STEWARD,
        ),
    ]
    dossier = {
        "dossier_id": "dos_data_ops",
        "entity_id": "PLATFORM-OPERATIONS",
        "headline": "Data Platform Operations and Service Level Objectives",
        "executive_summary": _summary(svc),
        "sections": [
            {
                "section_id": "sec_slos",
                "title": "Ingestion enforcement and recovery",
                "narrative_text": (
                    f"{replay.offered:,} transactions from the last week went through contract validation; "
                    f"{replay.rejected} were quarantined ({replay.false_rejects} healthy events refused). The "
                    f"warm-start restore drill rehydrated {drill.rows_restored:,} of {drill.rows_exported:,} rows "
                    f"in {drill.restore_ms:.0f} ms."
                ),
                "citations": ["contract_enforcement", "restore_drill_rows"],
                "metrics": metrics,
            }
        ],
        "as_of_timestamp": now_iso,
        "is_cached_snapshot": False,
    }
    canvas = {
        "canvas_type": "OPERATIONS_SLO",
        "payload": {
            "sla_statuses": svc.product_cards(),
            "error_budgets": svc.error_budgets(),
            "red_line_gates": red_line_payload(svc),
            "dlq": svc.dlq_records(),
        },
    }
    return _triage(svc, now_iso), dossier, canvas
