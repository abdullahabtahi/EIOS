"""Simulated Core Write-Back Sink with Chaos Fault Injection and Idempotency (US3)."""

from datetime import UTC, datetime
from enum import StrEnum
import json
import secrets
import threading
from typing import Any
import uuid

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.models import (
    ActionIntentToken,
    ExecutionReceipt,
    ExecutionStatus,
    LedgerEventType,
)
from eios.ontology.actions.sequencer import LedgerSequencer


class FaultMode(StrEnum):
    NONE = "NONE"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    LEDGER_CONFLICT = "LEDGER_CONFLICT"
    CORE_REJECTION = "CORE_REJECTION"


class SimulatedWriteBackSink:
    """Isolated operational write-back sink modeling core banking, payment gateways, and CRM systems."""

    def __init__(
        self,
        sequencer: LedgerSequencer | None = None,
        hot_state_engine: HotStateEngine | None = None,
    ) -> None:
        self.sequencer = sequencer
        self.hot_state = hot_state_engine
        self._fault_mode: FaultMode = FaultMode.NONE
        self._idempotency_cache: dict[str, ExecutionReceipt] = {}
        self._execution_history: list[ExecutionReceipt] = []
        self._lock = threading.Lock()

    def set_fault_mode(self, mode: FaultMode) -> None:
        """Configure chaos fault injection mode."""
        with self._lock:
            self._fault_mode = mode

    def get_execution_history(self) -> list[ExecutionReceipt]:
        with self._lock:
            return list(self._execution_history)

    def _compute_simulated_side_effects(
        self, action_type: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute realistic simulated operational mutations."""
        if action_type == "HoldWithdrawal":
            return {
                "withdrawal_status": "HELD",
                "clearinghouse_notified": True,
                "txn_id": parameters.get("txn_id"),
            }
        elif action_type == "FreezeAccount":
            return {
                "client_trading_state": "FROZEN",
                "withdrawal_disabled": True,
                "login_restricted": True,
                "client_id": parameters.get("client_id"),
            }
        elif action_type == "ClawbackCommission":
            return {
                "balance_debited_usd": float(parameters.get("amount", 0.0)),
                "partner_id": parameters.get("partner_id"),
                "recovery_ledger_updated": True,
            }
        elif action_type == "SuspendPartner":
            return {
                "partner_status": "SUSPENDED",
                "portal_disabled": True,
                "affiliate_links_deactivated": True,
                "partner_id": parameters.get("partner_id"),
            }
        elif action_type in ("LaunchRetentionPlaybook", "LaunchRetentionCampaign"):
            return {
                "campaign_activated": True,
                "budget_allocated_usd": float(parameters.get("budget", 0.0)),
                "notification_dispatched": True,
            }
        elif action_type == "AdjustPartnerTier":
            return {
                "tier_updated": parameters.get("target_tier"),
                "partner_id": parameters.get("partner_id"),
            }
        return {"mutation_applied": True, "action_type": action_type}

    def commit_action(
        self,
        token: ActionIntentToken,
        idempotency_key: str | None = None,
    ) -> ExecutionReceipt:
        """Commit an approved action intent to the simulated write-back sink with idempotency."""
        with self._lock:
            idem_key = idempotency_key or f"IDEM-{token.intent_id}"

            # Check idempotency cache
            if idem_key in self._idempotency_cache:
                return self._idempotency_cache[idem_key]

            receipt_id = str(uuid.uuid4())
            ext_txn_id = f"SIM-CORE-TXN-{secrets.token_hex(6).upper()}"
            now = datetime.now(UTC)

            # Evaluate fault injection
            if self._fault_mode == FaultMode.NONE:
                status = ExecutionStatus.COMMITTED
                side_effects = self._compute_simulated_side_effects(
                    token.action_type, token.parameters
                )
                comp_intent_id = None
                simulated_latency = 14.5
            elif self._fault_mode == FaultMode.NETWORK_TIMEOUT:
                status = ExecutionStatus.ABORTED
                side_effects = {"error": "Downstream core banking gateway timeout after 5000ms"}
                comp_intent_id = str(uuid.uuid4())
                simulated_latency = 5000.0
            elif self._fault_mode == FaultMode.LEDGER_CONFLICT:
                status = ExecutionStatus.ABORTED
                side_effects = {"error": "Optimistic lock collision on core balance row"}
                comp_intent_id = str(uuid.uuid4())
                simulated_latency = 32.0
            elif self._fault_mode == FaultMode.CORE_REJECTION:
                status = ExecutionStatus.REJECTED
                side_effects = {"error": "Core system policy engine rejected mutation"}
                comp_intent_id = None
                simulated_latency = 18.0
            else:
                status = ExecutionStatus.COMMITTED
                side_effects = {}
                comp_intent_id = None
                simulated_latency = 15.0

            receipt = ExecutionReceipt(
                receipt_id=receipt_id,
                intent_id=token.intent_id,
                idempotency_key=idem_key,
                external_transaction_id=ext_txn_id,
                action_type=token.action_type,
                status=status,
                simulated_latency_ms=simulated_latency,
                executed_at=now,
                side_effects=side_effects,
                compensation_intent_id=comp_intent_id,
            )

            self._idempotency_cache[idem_key] = receipt
            self._execution_history.append(receipt)

            # Persist to hot state
            if self.hot_state:
                self._persist_to_hot_state(receipt)

            # Record event in sequencer
            if self.sequencer:
                if status == ExecutionStatus.ABORTED:
                    self.sequencer.record_event(
                        event_type=LedgerEventType.ACTION_ABORTED,
                        entity_id=token.intent_id,
                        payload={
                            "receipt_id": receipt.receipt_id,
                            "intent_id": token.intent_id,
                            "status": status.value,
                            "compensation_intent_id": comp_intent_id,
                            "error": side_effects.get("error"),
                        },
                    )
                elif status == ExecutionStatus.REJECTED:
                    self.sequencer.record_event(
                        event_type=LedgerEventType.ACTION_REJECTED,
                        entity_id=token.intent_id,
                        payload={
                            "receipt_id": receipt.receipt_id,
                            "intent_id": token.intent_id,
                            "status": status.value,
                            "error": side_effects.get("error"),
                        },
                    )
                else:
                    self.sequencer.record_event(
                        event_type=LedgerEventType.ACTION_EXECUTED,
                        entity_id=token.intent_id,
                        payload={
                            "receipt_id": receipt.receipt_id,
                            "intent_id": token.intent_id,
                            "external_transaction_id": receipt.external_transaction_id,
                            "status": status.value,
                        },
                    )

            return receipt

    def _persist_to_hot_state(self, receipt: ExecutionReceipt) -> None:
        """Persist execution receipt into DuckDB simulated_writeback_ledger."""
        cursor = self.hot_state.get_cursor()
        cursor.execute(
            """
            INSERT INTO simulated_writeback_ledger (
                receipt_id, intent_id, idempotency_key, external_transaction_id,
                action_type, status, simulated_latency_ms, executed_at,
                side_effects, compensation_intent_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                receipt.receipt_id,
                receipt.intent_id,
                receipt.idempotency_key,
                receipt.external_transaction_id,
                receipt.action_type,
                receipt.status.value if hasattr(receipt.status, "value") else str(receipt.status),
                receipt.simulated_latency_ms,
                receipt.executed_at,
                json.dumps(receipt.side_effects),
                receipt.compensation_intent_id,
            ],
        )
