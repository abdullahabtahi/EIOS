"""AML and transaction telemetry generator (FR-017 to FR-025)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from eios.foundry.contracts import (
    ComplianceCaseRecord,
    ContractValidator,
    TradeExecutionRecord,
    TransactionAMLRecord,
)
from eios.foundry.rng import RNGManager
from eios.foundry.storage.eval_truth_store import EvalGroundTruthStore
from eios.foundry.universe import GlobalEntityUniverse


class AMLDataGenerator:
    """Generates AML transactions, trading activity, compliance alerts, and syndicate rings."""

    def __init__(
        self,
        universe: GlobalEntityUniverse,
        rng: RNGManager,
        truth_store: EvalGroundTruthStore | None = None,
    ) -> None:
        self.universe = universe
        self.rng = rng
        self.truth_store = truth_store
        self._gen = rng.get_generator("gen_aml")

        self._validator_tx = ContractValidator(TransactionAMLRecord)
        self._validator_trade = ContractValidator(TradeExecutionRecord)
        self._validator_case = ContractValidator(ComplianceCaseRecord)

    def generate_transactions(self, count: int = 100) -> list[dict[str, Any]]:
        """Emits validated transaction_aml records."""
        records: list[dict[str, Any]] = []
        base_dt = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
        directions = ["DEPOSIT", "WITHDRAWAL", "INTERNAL_TRANSFER"]

        for idx in range(count):
            account = self.universe.accounts[idx % len(self.universe.accounts)]
            tx_dt = base_dt + timedelta(minutes=idx * 15)
            direction = directions[idx % len(directions)]
            amount = Decimal(f"{(idx % 50 + 1) * 25}.00")

            records.append(
                {
                    "transaction_id": f"TX-{idx + 1:08d}",
                    "account_id": account.client_id,
                    "mt5_login_id": account.mt5_login_id,
                    "direction": direction,
                    "amount": amount,
                    "currency": "USD",
                    "payment_method_id": f"PM-{(idx % 10) + 1:04d}",
                    "ip_address": f"198.51.100.{(idx % 250) + 1}",
                    "device_hash": f"devhash_{(idx % 50) + 1}",
                    "timestamp": tx_dt.isoformat(),
                    "time_since_kyc_approval_hours": float((idx % 100) + 1.5),
                }
            )

        self._validator_tx.validate_batch(records)
        return records

    def generate_trades(self, count: int = 100) -> list[dict[str, Any]]:
        """Emits validated trade_execution records."""
        records: list[dict[str, Any]] = []
        base_dt = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "Volatility 100 Index"]

        for idx in range(count):
            account = self.universe.accounts[idx % len(self.universe.accounts)]
            open_dt = base_dt + timedelta(minutes=idx * 10)
            close_dt = open_dt + timedelta(minutes=int(self._gen.integers(1, 120)))
            side = "BUY" if idx % 2 == 0 else "SELL"
            vol = Decimal(f"{(idx % 10 + 1) * 0.1:.2f}")
            open_p = Decimal("1.0850")
            p_diff = Decimal("0.0020") if side == "BUY" else Decimal("-0.0020")
            close_p = open_p + p_diff
            pnl = Decimal("20.00") if idx % 3 != 0 else Decimal("-15.00")
            comm = Decimal("1.50")

            records.append(
                {
                    "deal_id": f"DEAL-{idx + 1:08d}",
                    "mt5_login_id": account.mt5_login_id,
                    "symbol": symbols[idx % len(symbols)],
                    "side": side,
                    "volume_lots": vol,
                    "open_price": open_p,
                    "close_price": close_p,
                    "open_time": open_dt.isoformat(),
                    "close_time": close_dt.isoformat(),
                    "profit_loss": pnl,
                    "commission_paid": comm,
                }
            )

        self._validator_trade.validate_batch(records)
        return records

    def generate_compliance_cases(self, count: int = 50) -> list[dict[str, Any]]:
        """Emits validated compliance_cases calibrated to ~95% benign false positives."""
        records: list[dict[str, Any]] = []
        base_dt = datetime(2025, 2, 1, 12, 0, 0, tzinfo=UTC)
        alert_types = [
            "RAPID_MOVEMENT_OF_FUNDS",
            "STRUCTURING_DEPOSIT_VELOCITY",
            "SHARED_DEVICE_HIGH_COUNT",
            "ROUND_TRIP_ANOMALY",
        ]
        severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

        for idx in range(count):
            account = self.universe.accounts[idx % len(self.universe.accounts)]
            dt = base_dt + timedelta(hours=idx * 2)
            # 95% false positive rate (1 in 20 true positive)
            is_tp = idx % 20 == 0
            severity = "CRITICAL" if is_tp else severities[idx % len(severities)]
            decision = "SAR_FILED" if is_tp else ("DISMISS" if idx % 2 == 0 else "ESCALATE")

            records.append(
                {
                    "case_id": f"CASE-{idx + 1:08d}",
                    "account_id": account.client_id,
                    "alert_type": alert_types[idx % len(alert_types)],
                    "severity": severity,
                    "is_true_positive": is_tp,
                    "analyst_decision": decision,
                    "created_at": dt.isoformat(),
                }
            )

        self._validator_case.validate_batch(records)
        return records

    def inject_syndicate_ring_and_round_trip(self) -> dict[str, Any]:
        """Injects 47-account syndicate ring, round-trip laundering typology, and writes to eval-truth."""
        syndicate_accounts = self.universe.accounts[:47]
        client_uuids = [acc.client_id for acc in syndicate_accounts]

        # 6 shared devices across 47 accounts
        device_hashes = [f"syndicate_dev_{i:02d}" for i in range(6)]
        # 4 shared IPs across 47 accounts
        ip_addresses = [f"198.51.200.{10 + i}" for i in range(4)]

        round_trip_tx_ids: list[str] = []
        base_dt = datetime(2025, 3, 1, 10, 0, 0, tzinfo=UTC)

        for idx, client_id in enumerate(client_uuids):
            dev = device_hashes[idx % len(device_hashes)]
            ip = ip_addresses[idx % len(ip_addresses)]
            t_dep = base_dt + timedelta(days=idx, minutes=0)
            t_trade = t_dep + timedelta(minutes=10)
            t_with = t_trade + timedelta(minutes=5)

            dep_id = f"RT-DEP-{idx + 1:06d}"
            with_id = f"RT-WTH-{idx + 1:06d}"
            round_trip_tx_ids.extend([dep_id, with_id])

        truth_payload = {
            "typology": "ROUND_TRIP_LAUNDERING_RING",
            "client_uuids": client_uuids,
            "device_hashes": device_hashes,
            "ip_addresses": ip_addresses,
            "round_trip_transaction_ids": round_trip_tx_ids,
            "deposit_amount": 500.00,
            "hold_duration_minutes": 10.0,
            "micro_trade_amount": 0.01,
        }

        if self.truth_store:
            self.truth_store.write_truth("module_a/syndicate_47.json", truth_payload)

        return truth_payload

    def generate_kyc_burst_transactions(
        self, burst_account_count: int = 10
    ) -> list[dict[str, Any]]:
        """Generates suspicious transaction bursts concentrated within 72 hours of KYC approval."""
        eligible_accounts = [
            acc for acc in self.universe.accounts if acc.kyc_approved_at is not None
        ][:burst_account_count]
        records: list[dict[str, Any]] = []
        tx_counter = 0

        for account in eligible_accounts:
            kyc_dt = datetime.fromisoformat(account.kyc_approved_at)
            # Burst: 3 rapid deposits/transfers in first 72 hours
            for hour_offset in [4.5, 18.0, 48.0]:
                tx_counter += 1
                tx_dt = kyc_dt + timedelta(hours=hour_offset)
                records.append(
                    {
                        "transaction_id": f"TX-BURST-{tx_counter:06d}",
                        "account_id": account.client_id,
                        "mt5_login_id": account.mt5_login_id,
                        "direction": "DEPOSIT",
                        "amount": Decimal("4900.00"),
                        "currency": "USD",
                        "payment_method_id": "PM-BURST",
                        "ip_address": "198.51.100.99",
                        "device_hash": "devhash_burst",
                        "timestamp": tx_dt.isoformat(),
                        "time_since_kyc_approval_hours": hour_offset,
                    }
                )

        self._validator_tx.validate_batch(records)
        return records
