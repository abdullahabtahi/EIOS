"""Pre-registered naive threshold rule baseline detector for partner fraud (Constitution Principle VI).

Authoritative References:
- docs/models_and_evals.md §4
- specs/009-partner-fraud/research.md §6

Pre-registered Baseline Rule:
Flag any two client accounts referred by different partners who execute trades
in the same currency pair in opposing directions (BUY vs SELL) within 30.0 seconds of each other.
"""

from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass(frozen=True)
class NaiveBaselinePrediction:
    account_a: str
    account_b: str
    partner_a: str
    partner_b: str
    symbol: str
    score: float
    flagged: bool


class NaiveOppositeTradeBaseline:
    """Naive threshold rule baseline for opposite trading detection.

    Rule:
    If account A (partner PA) and account B (partner PB, PA != PB) trade same symbol
    in opposite directions (BUY vs SELL) within max_time_delta_sec (default 30.0s),
    assign score = 1.0 (flagged), else 0.0.
    """

    def __init__(self, max_time_delta_sec: float = 30.0) -> None:
        self.max_time_delta_sec = max_time_delta_sec

    def evaluate_trades(self, trade_df: pd.DataFrame) -> list[NaiveBaselinePrediction]:
        """Run naive baseline over trade dataframe.

        Required columns: account_id, partner_id, symbol, direction, timestamp.
        """
        if trade_df.empty:
            return []

        df = trade_df.sort_values("timestamp").copy()
        predictions: list[NaiveBaselinePrediction] = []

        # Group by symbol to evaluate trades
        for symbol, group in df.groupby("symbol"):
            records = group.to_dict("records")
            n = len(records)
            for i in range(n):
                r1 = records[i]
                t1: datetime = r1["timestamp"]
                for j in range(i + 1, n):
                    r2 = records[j]
                    t2: datetime = r2["timestamp"]
                    delta_sec = (t2 - t1).total_seconds()
                    if delta_sec > self.max_time_delta_sec:
                        break

                    # Check different partners and accounts
                    if r1["partner_id"] != r2["partner_id"] and r1["account_id"] != r2["account_id"]:
                        is_opposite = (
                            (r1["direction"] == "BUY" and r2["direction"] == "SELL")
                            or (r1["direction"] == "SELL" and r2["direction"] == "BUY")
                        )
                        if is_opposite:
                            predictions.append(
                                NaiveBaselinePrediction(
                                    account_a=min(r1["account_id"], r2["account_id"]),
                                    account_b=max(r1["account_id"], r2["account_id"]),
                                    partner_a=r1["partner_id"] if r1["account_id"] < r2["account_id"] else r2["partner_id"],
                                    partner_b=r2["partner_id"] if r1["account_id"] < r2["account_id"] else r1["partner_id"],
                                    symbol=symbol,
                                    score=1.0,
                                    flagged=True,
                                )
                            )

        return predictions
