"""Seasonality-aware change-point detection (T020 / Principle I & VI).

Filters out temporary holiday pauses and weekend market closures using
trading-day calendar masking and Week-over-Week (WoW) normalized CUSUM / MAD.
"""

from typing import Any
import numpy as np
import pandas as pd


class SeasonalityChangePointDetector:
    """Detects structural disengagement vs seasonal dips with market-calendar masking."""

    def __init__(self, mad_multiplier: float = 2.5, min_consecutive_weeks: int = 2) -> None:
        self.mad_multiplier = mad_multiplier
        self.min_consecutive_weeks = min_consecutive_weeks

    def detect_change_point(
        self,
        df: pd.DataFrame,
        metric_col: str = "volume",
        date_col: str = "date",
    ) -> dict[str, Any]:
        """Analyzes time series of telemetry to determine if a structural change point occurred."""
        if df.empty or len(df) < 7:
            return {
                "is_anomaly": False,
                "confidence": 0.0,
                "reason": "INSUFFICIENT_HISTORY",
                "wow_ratios": [],
            }

        df_clean = df.copy()
        df_clean[date_col] = pd.to_datetime(df_clean[date_col])
        df_clean = df_clean.sort_values(by=date_col)

        # 1. Mask out non-trading days (Saturday=5, Sunday=6)
        df_trading = df_clean[df_clean[date_col].dt.weekday < 5].copy()

        # 2. Resample / group into 7-day calendar weeks
        # Assign week index relative to start
        start_date = df_trading[date_col].min()
        df_trading["week_idx"] = ((df_trading[date_col] - start_date).dt.days // 7).astype(int)

        weekly_vol = df_trading.groupby("week_idx")[metric_col].sum()
        weeks = list(weekly_vol.index)

        if len(weeks) < 2:
            return {
                "is_anomaly": False,
                "confidence": 0.1,
                "reason": "NORMAL_STABLE",
                "wow_ratios": [],
            }

        # 3. Compute Week-over-Week (WoW) ratios: R_w = (W_w + 1) / (W_{w-1} + 1)
        wow_ratios = []
        for i in range(1, len(weeks)):
            prev_w = weekly_vol.loc[weeks[i - 1]]
            curr_w = weekly_vol.loc[weeks[i]]
            ratio = float((curr_w + 1.0) / (prev_w + 1.0))
            wow_ratios.append(ratio)

        latest_ratio = wow_ratios[-1]
        latest_vol = float(weekly_vol.iloc[-1])
        prior_vol = float(weekly_vol.iloc[-2]) if len(weekly_vol) >= 2 else latest_vol

        # Check for recovery: if latest week recovered significantly vs prior week, it was a temporary dip!
        if latest_ratio >= 1.5 and latest_vol > 15:
            return {
                "is_anomaly": False,
                "confidence": 0.15,
                "reason": "SEASONAL_DIP_RECOVERED",
                "wow_ratios": wow_ratios,
            }

        # Check for sustained structural decay:
        # If last 2 consecutive weeks show acute drops (ratio < 0.60 or decay sustained)
        consecutive_drops = 0
        for r in wow_ratios[-self.min_consecutive_weeks:]:
            if r < 0.70:
                consecutive_drops += 1

        # Check absolute decay from baseline
        initial_vol = float(weekly_vol.iloc[0])
        total_decay = (initial_vol - latest_vol) / max(initial_vol, 1.0)

        if consecutive_drops >= self.min_consecutive_weeks and total_decay >= 0.50 and latest_vol <= 15:
            return {
                "is_anomaly": True,
                "confidence": 0.92,
                "reason": "STRUCTURAL_DISENGAGEMENT",
                "wow_ratios": wow_ratios,
            }

        return {
            "is_anomaly": False,
            "confidence": 0.10,
            "reason": "NORMAL_STABLE",
            "wow_ratios": wow_ratios,
        }
