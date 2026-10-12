"""Analyst decision label noise injection (FR-050)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from eios.foundry.rng import RNGManager


def inject_analyst_label_noise(
    records: List[Dict[str, Any]],
    rng: RNGManager,
    flip_rate: float = 0.05,
) -> List[Dict[str, Any]]:
    """Injects 3.0% to 8.0% label noise to simulate human analyst ambiguity."""
    gen = rng.get_generator("label_noise")
    noisy_records: List[Dict[str, Any]] = []

    # Map of flip decisions
    flip_map = {
        "DISMISS": "ESCALATE",
        "ESCALATE": "DISMISS",
        "SAR_FILED": "DISMISS",
    }

    for record in records:
        rec_copy = dict(record)
        # Uniform roll per record against target flip rate
        if gen.uniform(0.0, 1.0) < flip_rate:
            current_decision = rec_copy.get("analyst_decision")
            if current_decision in flip_map:
                rec_copy["analyst_decision"] = flip_map[current_decision]
                rec_copy["is_label_noisy"] = True
            elif "is_true_positive" in rec_copy:
                rec_copy["is_true_positive"] = not rec_copy["is_true_positive"]
                rec_copy["is_label_noisy"] = True
        else:
            rec_copy["is_label_noisy"] = False
        noisy_records.append(rec_copy)

    return noisy_records
