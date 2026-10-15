"""Fit the structural causal model from metric history and gate every edge on its own evidence (spec 034).

`SCMRunner` keeps the cached default model; this fits one from data. For each candidate edge it removes the effect of
the named confounders (Frisch-Waugh), standardises both series so the ridge penalty cannot shrink a small-scale
variable, runs the refutation battery, and keeps the edge only if every refuter passes. A planted control edge is
fitted the same way and is expected to fail: nothing forces its verdict. The weight is returned in the metrics' own
units, with a bootstrap interval.

Confidence is how stable the edge is, from three measurements: the share of bootstrap fits that agree on its sign,
and the discount for how far a random common cause and a random 80% subset move the estimate. It is a stability
score, not a probability. [ASSUMPTION]
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from eios.synthesis.models import CausalEdge, RefutationReport, SCMCacheManifest
from eios.synthesis.refutation import run_edge_refutation_suite
from eios.synthesis.scm import SCMCache

DEFAULT_BOOTSTRAP = 200
DEFAULT_PLACEBO_REPEATS = 5
MIN_POINTS = 60  # [ASSUMPTION] fewer daily points than this cannot support the refuter battery


@dataclass(frozen=True)
class CandidateEdge:
    source: str
    target: str
    rationale: str
    adjust: tuple[str, ...] = ()  # confounders to remove from both series before fitting
    control: bool = False  # a planted null: the gate is expected to reject it


@dataclass(frozen=True)
class FittedEdge:
    candidate: CandidateEdge
    weight: float  # target units per source unit, after adjustment
    ci_lower: float
    ci_upper: float
    confidence: float
    report: RefutationReport

    @property
    def passed(self) -> bool:
        return self.report.gate_verdict == "PASS"


@dataclass(frozen=True)
class FittedSCM:
    manifest: SCMCacheManifest  # the edges that passed, with every refutation report
    edges: tuple[FittedEdge, ...]  # every candidate, passed or not

    @property
    def cache(self) -> SCMCache:
        return SCMCache(self.manifest)

    @property
    def controls_rejected(self) -> bool:
        return all(not e.passed for e in self.edges if e.candidate.control)


def _residual(y: np.ndarray, controls: Sequence[np.ndarray]) -> np.ndarray:
    """`y` with the least-squares effect of the controls (and a constant) removed."""
    design = np.column_stack([np.ones(len(y)), *controls]) if controls else np.ones((len(y), 1))
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return np.asarray(y - design @ coef)


def _slope(t: np.ndarray, y: np.ndarray) -> float:
    tc = t - t.mean()
    denom = float(tc @ tc)
    return float(tc @ (y - y.mean()) / denom) if denom > 1e-18 else 0.0


def _bootstrap_slopes(
    t: np.ndarray, y: np.ndarray, draws: int, rng: np.random.Generator
) -> np.ndarray:
    idx = rng.integers(0, len(t), size=(draws, len(t)))
    ts, ys = t[idx], y[idx]
    tc = ts - ts.mean(axis=1, keepdims=True)
    denom = (tc * tc).sum(axis=1)
    safe = np.where(denom > 1e-18, denom, 1.0)
    return np.asarray(
        np.where(
            denom > 1e-18, (tc * (ys - ys.mean(axis=1, keepdims=True))).sum(axis=1) / safe, 0.0
        )
    )


def _standardise(x: np.ndarray) -> np.ndarray:
    sd = float(x.std())
    return np.asarray((x - x.mean()) / sd) if sd > 1e-18 else np.zeros_like(x)


def _confidence(boot: np.ndarray, point: float, report: RefutationReport) -> float:
    sign = np.sign(point)
    stable = float(np.mean(np.sign(boot) == sign)) if sign != 0 else 0.0
    shift = 1.0 - min(report.random_cause_delta_pct, 1.0)
    spread = 1.0 - min(report.subset_stability_delta_pct, 1.0)
    return round(stable * shift * spread, 4)


class EmpiricalSCMFitter:
    def __init__(
        self,
        candidates: Sequence[CandidateEdge],
        model_version: str,
        seed: int = 42,
        n_bootstrap: int = DEFAULT_BOOTSTRAP,
        placebo_repeats: int = DEFAULT_PLACEBO_REPEATS,
    ) -> None:
        self.candidates = tuple(candidates)
        self.model_version = model_version
        self.seed = seed
        self.n_bootstrap = n_bootstrap
        self.placebo_repeats = placebo_repeats

    def _fit_edge(
        self, spec: CandidateEdge, data: Mapping[str, np.ndarray], rng: np.random.Generator
    ) -> FittedEdge:
        controls = [data[c] for c in spec.adjust]
        t = _residual(data[spec.source], controls)
        y = _residual(data[spec.target], controls)
        weight = _slope(t, y)
        boot = _bootstrap_slopes(t, y, self.n_bootstrap, rng)
        edge_id = f"{spec.source}->{spec.target}"
        report = run_edge_refutation_suite(
            edge_id,
            _standardise(t),
            _standardise(y),
            is_placebo=False,  # a control is fitted like any edge; its verdict is whatever the data says
            n_bootstrap=self.n_bootstrap,
            rng=rng,
            placebo_repeats=self.placebo_repeats,
        )
        return FittedEdge(
            candidate=spec,
            weight=weight,
            ci_lower=float(np.percentile(boot, 2.5)),
            ci_upper=float(np.percentile(boot, 97.5)),
            confidence=_confidence(boot, weight, report),
            report=report,
        )

    def fit(self, data: Mapping[str, Sequence[float] | np.ndarray]) -> FittedSCM:
        arrays = {k: np.asarray(v, dtype=float).ravel() for k, v in data.items()}
        sizes = {len(v) for v in arrays.values()}
        if len(sizes) != 1 or min(sizes) < MIN_POINTS:
            raise ValueError(f"series must share one length of at least {MIN_POINTS} points")
        rng = np.random.default_rng(self.seed)
        fitted = tuple(self._fit_edge(c, arrays, rng) for c in self.candidates)
        digest = hashlib.sha256()
        for key in sorted(arrays):
            digest.update(key.encode())
            digest.update(arrays[key].tobytes())
        active = [
            CausalEdge(
                source_metric=e.candidate.source,
                target_metric=e.candidate.target,
                weight=round(e.weight, 6),
                ci_lower=round(e.ci_lower, 6),
                ci_upper=round(e.ci_upper, 6),
                confidence=e.confidence,
                rationale=e.candidate.rationale,
            )
            for e in fitted
            if e.passed and not e.candidate.control
        ]
        manifest = SCMCacheManifest(
            model_version=self.model_version,
            generated_at=datetime.now(UTC),
            git_sha="data-fit",
            dataset_hash=digest.hexdigest()[:16],
            edges=active,
            refutations={e.report.edge_id: e.report for e in fitted},
            active_edge_count=len(active),
            rejected_placebo_count=sum(1 for e in fitted if e.candidate.control and not e.passed),
        )
        return FittedSCM(manifest=manifest, edges=fitted)
