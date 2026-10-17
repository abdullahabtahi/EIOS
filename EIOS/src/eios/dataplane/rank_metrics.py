"""Ranking metrics shared by the engines' evaluations."""

from __future__ import annotations

import pandas as pd


def ranking_auc(scores: pd.Series, positives: frozenset[str]) -> float:
    """Probability a positive outranks a negative (Mann-Whitney); 0.0 when either side is empty, as nothing was measured."""
    ranks = scores.rank()
    is_pos = scores.index.isin(list(positives))
    n_pos, n_neg = int(is_pos.sum()), int((~is_pos).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.0
    return float((ranks[is_pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
