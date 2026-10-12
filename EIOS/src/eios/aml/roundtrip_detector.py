"""Rapid Round-Trip Structuring & Micro-P&L Laundering Detector (US3 / P1).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 3)
- .specify/memory/constitution.md (Principles I, VI)

Detects the money laundering pattern:
Deposit -> brief micro-trading with near-zero market exposure (net P&L ≈ $0.00) -> withdrawal within 72h of KYC approval.
"""

from datetime import datetime, timedelta, timezone
import math
import uuid
import numpy as np
import pandas as pd

from eios.aml.models import RoundTripTypology
from eios.ingestion.hot_state import HotStateEngine


class RoundTripDetector:
    """Identifies wash trading structuring and zero-market-risk turnover cycles."""

    def __init__(self, hot_state: HotStateEngine | None = None) -> None:
        self.hot_state = hot_state

    def detect_roundtrips(
        self,
        events_df: pd.DataFrame,
        window_hours: float = 72.0,
    ) -> list[RoundTripTypology]:
        """Scan event history and detect round-trip structuring sequences."""
        if events_df.empty:
            return []

        results: list[RoundTripTypology] = []
        df = events_df.copy()
        if "open_ts" in df.columns:
            if "timestamp" in df.columns:
                df["timestamp"] = df["timestamp"].fillna(df["open_ts"])
            else:
                df["timestamp"] = df["open_ts"]

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        cutoff_delta = timedelta(hours=window_hours)

        for client_id, client_events in df.groupby("client_id"):
            sorted_events = client_events.sort_values("timestamp")
            deposits = sorted_events[sorted_events["event_type"] == "DEPOSIT"]
            withdrawals = sorted_events[sorted_events["event_type"] == "WITHDRAWAL"]
            trades = sorted_events[sorted_events["event_type"] == "TRADE"]

            for _, dep in deposits.iterrows():
                dep_ts = dep["timestamp"]
                dep_amt = float(dep["amount"])
                kyc_dt = dep.get("kyc_approved_at", None)

                # Match subsequent withdrawals within window_hours
                subsequent_wdls = withdrawals[
                    (withdrawals["timestamp"] > dep_ts)
                    & (withdrawals["timestamp"] <= dep_ts + cutoff_delta)
                ]

                for _, wdl in subsequent_wdls.iterrows():
                    wdl_ts = wdl["timestamp"]
                    wdl_amt = float(wdl["amount"])

                    # Intervening trades
                    inter_trades = trades[
                        (trades["timestamp"] >= dep_ts) & (trades["timestamp"] <= wdl_ts)
                    ] if not trades.empty else pd.DataFrame()

                    trade_count = len(inter_trades)
                    if trade_count > 0:
                        net_pl = float(inter_trades["profit_loss"].sum())
                        pnl_series = inter_trades["profit_loss"].values
                        pnl_std = float(np.std(pnl_series)) if len(pnl_series) > 1 else 0.0

                        if "open_ts" in inter_trades.columns and "close_ts" in inter_trades.columns:
                            durations = (
                                pd.to_datetime(inter_trades["close_ts"])
                                - pd.to_datetime(inter_trades["open_ts"])
                            ).dt.total_seconds()
                            holding_secs = float(durations.median())
                        else:
                            holding_secs = 600.0  # default 10 minutes
                    else:
                        net_pl = 0.0
                        pnl_std = 0.0
                        holding_secs = 0.0

                    market_risk_pct = round(abs(net_pl) / max(dep_amt, 1.0), 5)
                    turnaround_hours = (wdl_ts - dep_ts).total_seconds() / 3600.0

                    if pd.notna(kyc_dt) and kyc_dt is not None:
                        hours_since_kyc = max(
                            0.0,
                            (dep_ts - pd.to_datetime(kyc_dt)).total_seconds() / 3600.0,
                        )
                    else:
                        hours_since_kyc = 500.0

                    # 1. Turnover symmetry factor (withdrawing near 100% of deposited capital)
                    ratio = wdl_amt / max(dep_amt, 0.01)
                    turnover_factor = math.exp(-abs(ratio - 1.0) * 5.0)

                    # 2. Near-zero market risk factor
                    if market_risk_pct <= 0.02:
                        zero_risk_score = 1.0 - (market_risk_pct / 0.02)
                    else:
                        zero_risk_score = 0.0

                    # 3. Holding duration factor (short holding duration <= 15 minutes)
                    if holding_secs <= 900.0:
                        duration_score = 1.0 - (holding_secs / 900.0) * 0.3
                    else:
                        duration_score = 0.2

                    # 4. KYC recency multiplier
                    kyc_multiplier = 1.35 if hours_since_kyc <= 72.0 else 0.75

                    # Scalper variance penalty (legitimate scalpers take directional volatility)
                    if trade_count >= 8 and pnl_std >= 10.0:
                        variance_penalty = 0.25
                    else:
                        variance_penalty = 1.0

                    # Composite round-trip risk score
                    raw_risk = (
                        0.40 * zero_risk_score
                        + 0.35 * turnover_factor
                        + 0.25 * duration_score
                    ) * kyc_multiplier * variance_penalty

                    # Micro-profit bonus ($0.01 to $0.05 laundering pattern specifically)
                    if abs(net_pl) <= 0.05 and trade_count >= 1:
                        raw_risk = max(raw_risk, 0.88)

                    typology_risk = round(float(np.clip(raw_risk, 0.05, 0.99)), 4)

                    results.append(
                        RoundTripTypology(
                            event_id=f"EV-RT-{uuid.uuid4().hex[:8].upper()}",
                            client_id=str(client_id),
                            deposit_txn_id=str(dep.get("txn_id") if "txn_id" in dep else dep.get("transaction_id", "TXN-DEP")),
                            withdrawal_txn_id=str(wdl.get("txn_id") if "txn_id" in wdl else wdl.get("transaction_id", "TXN-WTH")),
                            deposit_amount_usd=dep_amt,
                            withdrawal_amount_usd=wdl_amt,
                            trade_count=trade_count,
                            net_pl_usd=round(net_pl, 4),
                            market_risk_pct=market_risk_pct,
                            holding_duration_seconds=holding_secs,
                            hours_since_kyc=round(hours_since_kyc, 2),
                            typology_risk_score=typology_risk,
                        )
                    )

        return results

    def persist_events(self, events: list[RoundTripTypology]) -> int:
        """Persist detected round-trip events to DuckDB aml_roundtrip_events."""
        if not self.hot_state:
            return 0
        cursor = self.hot_state.get_cursor()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        count = 0
        for ev in events:
            cursor.execute(
                """
                INSERT OR REPLACE INTO aml_roundtrip_events (
                    event_id, client_id, deposit_txn_id, withdrawal_txn_id,
                    deposit_amount_usd, withdrawal_amount_usd, trade_count,
                    net_pl_usd, market_risk_pct, holding_duration_seconds,
                    hours_since_kyc, typology_risk_score, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ev.event_id,
                    ev.client_id,
                    ev.deposit_txn_id,
                    ev.withdrawal_txn_id,
                    ev.deposit_amount_usd,
                    ev.withdrawal_amount_usd,
                    ev.trade_count,
                    ev.net_pl_usd,
                    ev.market_risk_pct,
                    ev.holding_duration_seconds,
                    ev.hours_since_kyc,
                    ev.typology_risk_score,
                    now_str,
                ],
            )
            count += 1
        return count
