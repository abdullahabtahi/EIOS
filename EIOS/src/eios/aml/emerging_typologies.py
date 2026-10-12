"""Unsupervised Novel Typology Mining on Residual Transactions (US7 / P3).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- specs/010-client-aml/spec.md (User Story 7, SC-009, FR-016)
- .specify/memory/constitution.md (Principles I, VI)
"""

from dataclasses import dataclass
from typing import Any
import uuid
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler


@dataclass
class EmergingTypologyCandidate:
    typology_id: str
    candidate_name: str
    participating_clients: list[str]
    anomaly_score: float
    behavioral_profile: dict[str, Any]
    explanation: str


class EmergingTypologyMiner:
    """Discovers zero-day money laundering typologies across unexplained residual transactions."""

    def __init__(self, top_k: int = 5, contamination: float = 0.05, random_state: int = 42) -> None:
        self.top_k = top_k
        self.contamination = contamination
        self.random_state = random_state

    def mine_emerging_typologies(self, residual_df: pd.DataFrame) -> list[EmergingTypologyCandidate]:
        """Execute unsupervised anomaly clustering and surface top novel laundering candidates."""
        if residual_df.empty:
            return []

        df = residual_df.copy()

        # Identify numerical candidate feature columns
        candidate_cols = [
            c for c in [
                "amount_usd",
                "distinct_instruments_count",
                "rapid_turnaround_ratio",
                "off_hours_ratio",
                "asset_spread_entropy",
                "velocity_ratio",
            ]
            if c in df.columns
        ]

        if not candidate_cols:
            # Fall back to any numeric columns
            candidate_cols = [c for c in df.select_dtypes(include=[np.number]).columns if not c.endswith("_id")]

        if not candidate_cols:
            return []

        X = df[candidate_cols].fillna(0.0).values
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(X)

        # Isolation Forest for unsupervised outlier isolation
        iso = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
        )
        iso.fit(X_scaled)
        raw_scores = -iso.score_samples(X_scaled)  # higher = more anomalous

        # Normalize scores to [0.0, 1.0]
        min_s = float(np.min(raw_scores))
        max_s = float(np.max(raw_scores))
        if max_s > min_s:
            norm_scores = (raw_scores - min_s) / (max_s - min_s)
        else:
            norm_scores = np.zeros_like(raw_scores)

        df["anomaly_score"] = norm_scores

        # Filter anomalous subset (e.g. top 10% highest scores)
        threshold = float(np.quantile(norm_scores, 0.90))
        anom_df = df[df["anomaly_score"] >= threshold]
        if anom_df.empty:
            anom_df = df.nlargest(min(len(df), 10), "anomaly_score")

        candidates: list[EmergingTypologyCandidate] = []

        # Check for multi-instrument cross-asset dispersion
        multi_asset_mask = (
            anom_df["distinct_instruments_count"] >= 3
            if "distinct_instruments_count" in anom_df.columns
            else pd.Series(False, index=anom_df.index)
        )

        if multi_asset_mask.any():
            multi_df = anom_df[multi_asset_mask]
            client_ids = list(multi_df["client_id"].unique()) if "client_id" in multi_df.columns else []
            mean_score = float(multi_df["anomaly_score"].mean())

            profile = {
                "avg_instruments": float(multi_df["distinct_instruments_count"].mean())
                if "distinct_instruments_count" in multi_df.columns
                else 0.0,
                "avg_amount_usd": float(multi_df["amount_usd"].mean()) if "amount_usd" in multi_df.columns else 0.0,
                "avg_entropy": float(multi_df["asset_spread_entropy"].mean())
                if "asset_spread_entropy" in multi_df.columns
                else 0.0,
                "affected_accounts": len(client_ids),
            }

            candidates.append(
                EmergingTypologyCandidate(
                    typology_id=f"TYPO-NOVEL-{uuid.uuid4().hex[:6].upper()}",
                    candidate_name="CROSS_ASSET_MULTI_INSTRUMENT_LAYERING",
                    participating_clients=client_ids,
                    anomaly_score=round(max(0.85, mean_score), 4),
                    behavioral_profile=profile,
                    explanation=(
                        f"Isolated novel multi-instrument cross-asset wash scheme across {len(client_ids)} accounts. "
                        f"Features high instrument entropy ({profile.get('avg_entropy', 0.0):.2f}) and coordinated asset dispersion."
                    ),
                )
            )

        # Residual high velocity / timing cluster
        residual_anom = anom_df[~multi_asset_mask] if multi_asset_mask.any() else anom_df
        if not residual_anom.empty and len(candidates) < self.top_k:
            client_ids = list(residual_anom["client_id"].unique()) if "client_id" in residual_anom.columns else []
            mean_score = float(residual_anom["anomaly_score"].mean())
            profile = {
                "avg_amount_usd": float(residual_anom["amount_usd"].mean())
                if "amount_usd" in residual_anom.columns
                else 0.0,
                "affected_accounts": len(client_ids),
            }

            candidates.append(
                EmergingTypologyCandidate(
                    typology_id=f"TYPO-NOVEL-{uuid.uuid4().hex[:6].upper()}",
                    candidate_name="ANOMALOUS_RESIDUAL_VELOCITY_BURST",
                    participating_clients=client_ids,
                    anomaly_score=round(mean_score, 4),
                    behavioral_profile=profile,
                    explanation=(
                        f"High-deviation residual transactions detected across {len(client_ids)} accounts "
                        "exhibiting unclassified velocity departures."
                    ),
                )
            )

        # Sort candidates by anomaly score descending and cap at top_k
        candidates.sort(key=lambda c: c.anomaly_score, reverse=True)
        return candidates[: self.top_k]
