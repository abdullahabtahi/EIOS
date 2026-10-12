"""Module B Baseline: Naive Opposite Trade Matcher for Partner Fraud (T034).

Baseline to beat: 1-hop heuristic "Same instrument, opposite direction within N s".
Candidate model commitment: Graph temporal symmetry + direction anti-correlation beating naive FPR on hedgers by >= 20%.
"""

from typing import Any


class NaiveOppositeTradeBaseline:
    """1-hop opposite trade matcher checking temporal proximity and inverted direction."""

    def __init__(self, time_window_seconds: float = 10.0) -> None:
        self.time_window = time_window_seconds

    def find_opposite_pairs(self, trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        flagged_pairs: list[dict[str, Any]] = []
        n = len(trades)

        for i in range(n):
            for j in range(i + 1, n):
                t1 = trades[i]
                t2 = trades[j]

                same_inst = t1.get("instrument") == t2.get("instrument")
                diff_partner = t1.get("partner_id") != t2.get("partner_id")
                dir1 = str(t1.get("direction")).upper()
                dir2 = str(t2.get("direction")).upper()
                opposite_dir = (dir1 == "BUY" and dir2 == "SELL") or (
                    dir1 == "SELL" and dir2 == "BUY"
                )

                dt = abs(float(t1.get("timestamp", 0.0)) - float(t2.get("timestamp", 0.0)))
                within_window = dt <= self.time_window

                if same_inst and diff_partner and opposite_dir and within_window:
                    flagged_pairs.append(
                        {
                            "trade_a": t1.get("trade_id"),
                            "trade_b": t2.get("trade_id"),
                            "dt_seconds": dt,
                            "instrument": t1.get("instrument"),
                        }
                    )

        return flagged_pairs


def evaluate_opposite_trades(trades: list[dict[str, Any]]) -> dict[str, float]:
    baseline = NaiveOppositeTradeBaseline()
    pairs = baseline.find_opposite_pairs(trades)

    flagged_trade_ids = set()
    for p in pairs:
        flagged_trade_ids.add(p["trade_a"])
        flagged_trade_ids.add(p["trade_b"])

    tp = sum(1 for t in trades if t.get("trade_id") in flagged_trade_ids and t.get("is_fraud") == 1)
    fp = sum(1 for t in trades if t.get("trade_id") in flagged_trade_ids and t.get("is_fraud") == 0)
    fn = sum(
        1 for t in trades if t.get("trade_id") not in flagged_trade_ids and t.get("is_fraud") == 1
    )

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "flagged_pairs_count": float(len(pairs)),
    }
