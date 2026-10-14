"""The causal claim an AML dossier may make, gated by the placebo refuter (spec 031 FR-012, RL-3).

The claim is "being in a mule ring drives pass-through behaviour": treatment is ring membership across all clients,
outcome is the share of deposits withdrawn. It is shown as causal only when the whole refutation battery passes;
otherwise the dossier says correlation only. The same verdict applies to every ring case in the snapshot.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from eios.aml.models import MuleRingCluster
from eios.synthesis.models import RefutationReport
from eios.synthesis.refutation import run_edge_refutation_suite

EDGE_ID = "ring_membership->pass_through"
_SEED = 20261014


def ring_refutation(facts: pd.DataFrame, clusters: list[MuleRingCluster]) -> RefutationReport:
    members = {m for c in clusters if c.is_syndicate for m in c.member_client_ids}
    active = facts[facts["dep_volume"] > 0]
    treatment = active.index.isin(members).astype(float)
    outcome = active["dw_ratio"].to_numpy(dtype=float)
    return run_edge_refutation_suite(EDGE_ID, treatment, outcome, rng=np.random.default_rng(_SEED))
