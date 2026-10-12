"""Time-Bucketed Candidate Pruning & Statistical Anti-Correlation Pair Detector (US1 / Module B).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US1, FR-001, FR-002, FR-003)
- specs/009-partner-fraud/research.md §1
"""

from collections import defaultdict
from datetime import UTC, datetime
import math
import numpy as np
import pandas as pd

from eios.fraud.models import DirectionalType, TradingPairCorrelation
from eios.ingestion.hot_state import HotStateEngine


class TimeBucketedPairDetector:
    """Detects coordinated opposite and mirror trading pairs across affiliate portfolios.

    Two-stage detection pipeline:
    1. Candidate Hashing: Partition trades into overlapping sliding buckets (default 30s)
       indexed by (symbol, bucket_id). Only pairs under distinct partners co-occurring
       in >= min_co_occurrences buckets enter candidate scoring.
    2. Bilateral Multi-Factor Correlation:
       - Directional alignment (OPPOSITE if anti-correlated, MIRROR if lockstep)
       - Volume symmetry (Sym(V_i, V_j) = 1.0 - |V_i - V_j| / max(V_i, V_j))
       - Exponential timing proximity (exp(-delta_t / tau))
       - Zero-sum P&L extraction ratio
       - Composite collusion score
    """

    def __init__(
        self,
        bucket_window_sec: float = 30.0,
        tau_timing_sec: float = 5.0,
        min_co_occurrences: int = 3,
        min_collusion_confidence: float = 0.50,
        w_dir: float = 0.30,
        w_sym: float = 0.25,
        w_timing: float = 0.25,
        w_zero_sum: float = 0.20,
    ) -> None:
        self.bucket_window_sec = bucket_window_sec
        self.tau_timing_sec = tau_timing_sec
        self.min_co_occurrences = min_co_occurrences
        self.min_collusion_confidence = min_collusion_confidence
        self.w_dir = w_dir
        self.w_sym = w_sym
        self.w_timing = w_timing
        self.w_zero_sum = w_zero_sum

    def detect_pairs(self, trade_df: pd.DataFrame) -> list[TradingPairCorrelation]:
        """Execute candidate pruning and bilateral scoring over trade log."""
        if trade_df.empty:
            return []

        df = trade_df.sort_values("timestamp").copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Stage 1: Candidate Hashing
        # To handle boundary conditions, assign trades to overlapping half-window buckets
        step_sec = self.bucket_window_sec / 2.0
        min_ts = df["timestamp"].min()

        df["epoch_sec"] = (df["timestamp"] - min_ts).dt.total_seconds()
        df["bucket_0"] = (df["epoch_sec"] // step_sec).astype(int)
        df["bucket_1"] = df["bucket_0"] + 1

        # Map candidate pair to list of co-occurring trade comparisons
        # key: (min(acc_a, acc_b), max(acc_a, acc_b))
        candidate_co_occurrences: dict[tuple[str, str], list[dict]] = defaultdict(list)
        candidate_meta: dict[tuple[str, str], tuple[str, str, str]] = {}

        # Evaluate trades co-occurring in each bucket
        for symbol, sym_group in df.groupby("symbol"):
            records = sym_group.to_dict("records")
            n = len(records)
            for i in range(n):
                r1 = records[i]
                t1 = r1["epoch_sec"]
                for j in range(i + 1, n):
                    r2 = records[j]
                    t2 = r2["epoch_sec"]
                    delta_t = t2 - t1
                    if delta_t > self.bucket_window_sec:
                        break

                    # Exclude same account or same affiliate
                    if r1["account_id"] == r2["account_id"] or r1["partner_id"] == r2["partner_id"]:
                        continue

                    acc_a = min(r1["account_id"], r2["account_id"])
                    acc_b = max(r1["account_id"], r2["account_id"])
                    part_a = r1["partner_id"] if r1["account_id"] == acc_a else r2["partner_id"]
                    part_b = r2["partner_id"] if r1["account_id"] == acc_a else r1["partner_id"]
                    pair_key = (acc_a, acc_b)

                    candidate_meta[pair_key] = (part_a, part_b, symbol)

                    rec_a = r1 if r1["account_id"] == acc_a else r2
                    rec_b = r2 if r2["account_id"] == acc_b else r1

                    candidate_co_occurrences[pair_key].append({
                        "delta_t": delta_t,
                        "dir_a": rec_a["direction"],
                        "dir_b": rec_b["direction"],
                        "lots_a": rec_a["lots"],
                        "lots_b": rec_b["lots"],
                        "pnl_a": rec_a.get("pnl_usd", 0.0),
                        "pnl_b": rec_b.get("pnl_usd", 0.0),
                        "comm_a": rec_a.get("commission_usd", 0.0),
                        "comm_b": rec_b.get("commission_usd", 0.0),
                    })

        # Stage 2: Bilateral Correlation Scoring
        flagged_pairs: list[TradingPairCorrelation] = []

        for pair_key, occurrences in candidate_co_occurrences.items():
            if len(occurrences) < self.min_co_occurrences:
                continue

            acc_a, acc_b = pair_key
            part_a, part_b, symbol = candidate_meta[pair_key]

            co_count = len(occurrences)
            delta_ts = [o["delta_t"] for o in occurrences]
            within_15s_count = sum(1 for dt in delta_ts if dt <= 15.0)
            timing_pct = (within_15s_count / co_count) * 100.0

            # Directional anti-correlation vs mirror correlation
            opposite_count = sum(
                1 for o in occurrences if (o["dir_a"] != o["dir_b"])
            )
            mirror_count = sum(
                1 for o in occurrences if (o["dir_a"] == o["dir_b"])
            )

            if opposite_count >= mirror_count:
                directional_type = DirectionalType.OPPOSITE
                dir_alignment_score = opposite_count / co_count
            else:
                directional_type = DirectionalType.MIRROR
                dir_alignment_score = mirror_count / co_count

            # Volume Symmetry
            sym_scores = [
                1.0 - (abs(o["lots_a"] - o["lots_b"]) / max(o["lots_a"], o["lots_b"], 1e-6))
                for o in occurrences
            ]
            mean_sym = float(np.mean(sym_scores))

            # Exponential timing proximity
            timing_scores = [math.exp(-dt / self.tau_timing_sec) for dt in delta_ts]
            mean_timing_score = float(np.mean(timing_scores))

            # Net P&L and Zero-Sum Ratio / Lockstep Symmetry
            total_pnl_a = sum(o["pnl_a"] for o in occurrences)
            total_pnl_b = sum(o["pnl_b"] for o in occurrences)
            combined_net_pl = total_pnl_a + total_pnl_b
            total_commission = sum(o["comm_a"] + o["comm_b"] for o in occurrences)

            if directional_type == DirectionalType.OPPOSITE:
                if total_commission > 0:
                    zero_sum_ratio = 1.0 - min(1.0, abs(combined_net_pl) / (total_commission + 1e-6))
                else:
                    zero_sum_ratio = 0.50
                coordination_pl_score = zero_sum_ratio
            else:
                # For mirror trading: lockstep P&L symmetry (both make/lose identical amounts)
                denom = abs(total_pnl_a) + abs(total_pnl_b) + 1e-6
                lockstep_symmetry = 1.0 - min(1.0, abs(total_pnl_a - total_pnl_b) / denom)
                zero_sum_ratio = 0.0
                coordination_pl_score = lockstep_symmetry

            # Composite Collusion Confidence
            collusion_confidence = (
                self.w_dir * dir_alignment_score
                + self.w_sym * mean_sym
                + self.w_timing * mean_timing_score
                + self.w_zero_sum * coordination_pl_score
            )
            collusion_confidence = max(0.0, min(1.0, collusion_confidence))

            if collusion_confidence >= self.min_collusion_confidence:
                pair_id = f"PAIR-{symbol}-{acc_a}-{acc_b}"
                flagged_pairs.append(
                    TradingPairCorrelation(
                        pair_id=pair_id,
                        account_a=acc_a,
                        partner_a=part_a,
                        account_b=acc_b,
                        partner_b=part_b,
                        symbol=symbol,
                        co_occurrence_count=co_count,
                        timing_correlation_pct=round(timing_pct, 2),
                        directional_type=directional_type,
                        size_symmetry_score=round(mean_sym, 4),
                        combined_net_pl_usd=round(combined_net_pl, 2),
                        total_commission_extracted_usd=round(total_commission, 2),
                        zero_sum_ratio=round(zero_sum_ratio, 4),
                        collusion_confidence=round(collusion_confidence, 4),
                    )
                )

        # Sort pairs by collusion confidence descending
        flagged_pairs.sort(key=lambda p: p.collusion_confidence, reverse=True)
        return flagged_pairs

    def persist_pairs_to_hot_state(
        self,
        hot_state: HotStateEngine,
        pairs: list[TradingPairCorrelation],
    ) -> int:
        """Persist detected trading pairs into partner_opposite_trading_pairs DuckDB table."""
        cursor = hot_state.get_cursor()
        now = datetime.now(UTC)
        count = 0

        for pair in pairs:
            cursor.execute(
                """
                INSERT OR REPLACE INTO partner_opposite_trading_pairs (
                    pair_id, partner_a, account_a, partner_b, account_b,
                    symbol, co_occurrence_count, timing_correlation_pct,
                    directional_type, combined_net_pl_usd, total_commission_usd,
                    collusion_confidence, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    pair.pair_id,
                    pair.partner_a,
                    pair.account_a,
                    pair.partner_b,
                    pair.account_b,
                    pair.symbol,
                    pair.co_occurrence_count,
                    pair.timing_correlation_pct,
                    pair.directional_type.value,
                    pair.combined_net_pl_usd,
                    pair.total_commission_extracted_usd,
                    pair.collusion_confidence,
                    now,
                ],
            )
            count += 1

        return count
