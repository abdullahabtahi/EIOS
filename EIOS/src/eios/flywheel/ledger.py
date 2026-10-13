"""Thread-safe Multi-Horizon Decision Outcomes Ledger Repository."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime
from typing import Any

from eios.flywheel.models import DecisionOutcomeRecord, MilestoneStatus


def compute_record_lineage_hash(  # noqa: PLR0913
    decision_id: str,
    intent_id: str,
    timestamp: datetime | str,
    entity_id: str,
    action_type: str,
    propensity_score: float,
    treatment_assigned: bool,
    prev_hash: str = "GENESIS",
) -> str:
    """Computes deterministic SHA-256 digest over core proposal parameters."""
    ts_str = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
    payload = {
        "decision_id": decision_id,
        "intent_id": intent_id,
        "timestamp": ts_str,
        "entity_id": entity_id,
        "action_type": action_type,
        "propensity_score": round(float(propensity_score), 6),
        "treatment_assigned": bool(treatment_assigned),
        "prev_hash": prev_hash,
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class DecisionOutcomesLedger:
    """Thread-safe multi-horizon decision outcomes repository and reconciliation store."""

    def __init__(self) -> None:
        self._records: dict[str, DecisionOutcomeRecord] = {}
        self._intent_index: dict[str, str] = {}
        self._entity_index: dict[str, list[str]] = {}
        self._lock = threading.RLock()
        self._last_hash = "GENESIS"

    def append_decision(
        self,
        record: DecisionOutcomeRecord,
    ) -> DecisionOutcomeRecord:
        """Appends a new decision outcome record to the immutable ledger."""
        with self._lock:
            if record.decision_id in self._records:
                raise ValueError(f"Decision ID '{record.decision_id}' already exists in ledger")

            # Verify or stamp provenance hash
            if not record.provenance_hash or record.provenance_hash == "AUTO":
                prov_hash = compute_record_lineage_hash(
                    decision_id=record.decision_id,
                    intent_id=record.intent_id,
                    timestamp=record.timestamp,
                    entity_id=record.entity_id,
                    action_type=record.action_type,
                    propensity_score=record.propensity_score,
                    treatment_assigned=record.treatment_assigned,
                    prev_hash=self._last_hash,
                )
                record = record.model_copy(update={"provenance_hash": prov_hash})

            self._records[record.decision_id] = record
            self._intent_index[record.intent_id] = record.decision_id

            if record.entity_id not in self._entity_index:
                self._entity_index[record.entity_id] = []
            self._entity_index[record.entity_id].append(record.decision_id)

            self._last_hash = record.provenance_hash
            return record

    def get_by_id(self, decision_id: str) -> DecisionOutcomeRecord | None:
        """Retrieves record by decision ID."""
        with self._lock:
            return self._records.get(decision_id)

    def get_by_intent_id(self, intent_id: str) -> DecisionOutcomeRecord | None:
        """Retrieves record by intent ID."""
        with self._lock:
            decision_id = self._intent_index.get(intent_id)
            if decision_id:
                return self._records.get(decision_id)
            return None

    def get_by_entity(self, entity_id: str) -> list[DecisionOutcomeRecord]:
        """Retrieves all records for an entity."""
        with self._lock:
            ids = self._entity_index.get(entity_id, [])
            return [self._records[did] for did in ids if did in self._records]

    def query_records(  # noqa: C901, PLR0913
        self,
        service_name: str | None = None,
        action_type: str | None = None,
        entity_type: str | None = None,
        treatment_assigned: bool | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        horizon_filter: str | None = None,
        horizon_status: MilestoneStatus | None = None,
    ) -> list[DecisionOutcomeRecord]:
        """Queries records by multiple operational filters."""
        with self._lock:
            results: list[DecisionOutcomeRecord] = []
            for record in self._records.values():
                if service_name and record.service_name != service_name:
                    continue
                if action_type and record.action_type != action_type:
                    continue
                if entity_type and record.entity_type != entity_type:
                    continue
                if (
                    treatment_assigned is not None
                    and record.treatment_assigned != treatment_assigned
                ):
                    continue
                if start_time and record.timestamp < start_time:
                    continue
                if end_time and record.timestamp > end_time:
                    continue
                if horizon_filter:
                    if (
                        horizon_filter == "30d"
                        and horizon_status
                        and record.status_30d != horizon_status
                    ):
                        continue
                    elif (
                        horizon_filter == "60d"
                        and horizon_status
                        and record.status_60d != horizon_status
                    ):
                        continue
                    elif (
                        horizon_filter == "90d"
                        and horizon_status
                        and record.status_90d != horizon_status
                    ):
                        continue

                results.append(record)

            return sorted(results, key=lambda r: r.timestamp)

    def update_milestone(
        self,
        decision_id: str,
        horizon: str,
        actual_impact: float,
        status: MilestoneStatus = MilestoneStatus.RECONCILED,
    ) -> DecisionOutcomeRecord:
        """Updates a milestone horizon (30d, 60d, or 90d) with realized actual and computes residual."""
        with self._lock:
            record = self._records.get(decision_id)
            if not record:
                raise KeyError(f"Decision ID '{decision_id}' not found in ledger")

            actual_val = float(actual_impact)
            updates: dict[str, Any] = {}

            if horizon == "30d":
                residual = actual_val - record.predicted_impact_30d
                updates = {
                    "actual_impact_30d": actual_val,
                    "residual_30d": round(residual, 4),
                    "status_30d": status,
                }
            elif horizon == "60d":
                residual = actual_val - record.predicted_impact_60d
                updates = {
                    "actual_impact_60d": actual_val,
                    "residual_60d": round(residual, 4),
                    "status_60d": status,
                }
            elif horizon == "90d":
                residual = actual_val - record.predicted_impact_90d
                updates = {
                    "actual_impact_90d": actual_val,
                    "residual_90d": round(residual, 4),
                    "status_90d": status,
                }
            else:
                raise ValueError(f"Invalid horizon '{horizon}'. Must be '30d', '60d', or '90d'.")

            updated_record = record.model_copy(update=updates)
            self._records[decision_id] = updated_record
            return updated_record

    def count(self) -> int:
        """Returns total records count."""
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        """Clears all records from the ledger."""
        with self._lock:
            self._records.clear()
            self._intent_index.clear()
            self._entity_index.clear()
            self._last_hash = "GENESIS"
