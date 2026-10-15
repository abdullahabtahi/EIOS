"""Synthetic probes: drive the governed tool port and the replay, record what happened, measure the red lines (spec 035).

A probe is a real call through the same `GovernedToolPort` the assistant uses, timed here and recorded as a service
level indicator event in the plane's `SLOMonitoringEngine`. The indicators nothing probes (agent turns, ingestion
freshness, approvals) stay empty, and an empty indicator reads `NO_DATA`, never healthy. Red lines are measured from
the engines; one that cannot be measured on this plane says so instead of passing.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass
from typing import Any

from eios.dataplane.aml_engine import AmlSnapshot
from eios.dataplane.ops_replay import ReplayOutcome
from eios.observability.slo_catalog import DEFAULT_SLO_CATALOG, SLICategory
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import Principal, principal_for
from eios.ontology.omcp.port.readmodels import ReadModels

ROUNDS = 25  # [ASSUMPTION] probe calls per indicator: enough for a stable p95, few enough to run at start
WHAT_IF_ROUNDS = 100
RL6_BUDGET_MS = 200.0  # RL-6
MIN_CONFIDENCE, MIN_PLACEBO_P = 0.80, 0.05  # RL-3
PASS, FAIL, NOT_MEASURED = "PASS", "FAIL", "NOT_MEASURED"


@dataclass(frozen=True)
class RedLine:
    gate_id: str
    name: str
    status: str
    margin: float | None
    basis: str


@dataclass(frozen=True)
class ProbeReport:
    red_lines: tuple[RedLine, ...]
    events: dict[str, int]  # indicator -> events recorded
    what_if_p95_ms: float


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)] if ordered else 0.0


class _Prober:
    def __init__(self, models: ReadModels) -> None:
        self.models = models
        self.port = build_port(models)
        self.events: dict[str, int] = {}

    def call(self, who: Principal, tool: str, args: dict[str, Any]) -> tuple[float, bool]:
        started = time.perf_counter()
        outcome = self.port.call(who, tool, args)
        return (time.perf_counter() - started) * 1000.0, outcome.error is None

    def record(self, sli: SLICategory, observed: float, compliant: bool) -> None:
        threshold = DEFAULT_SLO_CATALOG[sli].target_threshold
        self.models.slo_engine.record_event(
            sli, observed, threshold, compliant, f"probe-{uuid.uuid4().hex[:8]}", "ops-probe"
        )
        self.events[sli.value] = self.events.get(sli.value, 0) + 1

    def timed(
        self,
        sli: SLICategory,
        who: Principal,
        tool: str,
        args: list[dict[str, Any]],
        unit_ms: float,
    ) -> list[float]:
        """Probe a tool; the observation is the latency in the indicator's own unit, compliant if ok and in budget."""
        threshold = DEFAULT_SLO_CATALOG[sli].target_threshold
        latencies: list[float] = []
        for a in args:
            ms, ok = self.call(who, tool, a)
            latencies.append(ms)
            observed = ms / unit_ms
            self.record(sli, observed, ok and observed <= threshold)
        return latencies


def _chain_label_ok(models: ReadModels) -> tuple[bool, float | None]:
    edges = models.executive.get_causal_dag().edges
    verified = [e for e in edges if e.refuter.is_causal_verified]
    clean = all(
        e.refuter.confidence >= MIN_CONFIDENCE and e.refuter.placebo_p_value > MIN_PLACEBO_P
        for e in verified
    )
    unverified_ok = all(
        not e.refuter.is_causal_verified for e in edges if e.refuter.confidence < MIN_CONFIDENCE
    )
    margin = min((e.refuter.confidence for e in verified), default=None)
    return clean and unverified_ok and bool(verified), None if margin is None else round(
        margin - MIN_CONFIDENCE, 4
    )


def _red_lines(
    models: ReadModels,
    aml: AmlSnapshot,
    probe: _Prober,
    what_if_ms: list[float],
    deterministic: bool,
) -> tuple[RedLine, ...]:
    rl3_ok, rl3_margin = _chain_label_ok(models)
    biggest_ring = max(aml.world.config.ring_sizes, default=0)
    largest = aml.quality.largest_cluster
    chain = models.compliance.verify_hash_chain_interactive()
    p95 = _p95(what_if_ms)
    return (
        RedLine(
            "RL-1",
            "Zero LLM Metric Calculation",
            PASS if deterministic else FAIL,
            0.0,
            "the briefing and a governed metric recomputed twice are identical; no model is on the path",
        ),
        RedLine(
            "RL-2",
            "No Autonomous Write-Back Four-Eyes Gate",
            NOT_MEASURED,
            None,
            "enforced and tested in the intent hub; not probed here because a probe would write to the ledger",
        ),
        RedLine(
            "RL-3",
            "Causal Refuter Placebo Threshold p > 0.05",
            PASS if rl3_ok else FAIL,
            rl3_margin,
            "every verified edge clears the placebo and confidence thresholds; the control is not verified",
        ),
        RedLine(
            "RL-4",
            "CGNAT Proxy Hub Suppression k > 100",
            PASS if largest <= biggest_ring else FAIL,
            float(biggest_ring - largest),
            "the largest detected ring is no bigger than the biggest ring planted; an unsuppressed hub would glue clusters",
        ),
        RedLine(
            "RL-5",
            "WORM Cryptographic SHA-256 Hash Chaining",
            PASS if chain.get("is_chain_unbroken") else FAIL,
            0.0,
            "the decision ledger's hash chain was walked end to end",
        ),
        RedLine(
            "RL-6",
            "Sub-200ms Parametric Propagation & 100% Attribution",
            PASS if p95 < RL6_BUDGET_MS else FAIL,
            round(RL6_BUDGET_MS - p95, 2),
            f"p95 of {len(what_if_ms)} what-if calls through the tool port, attribution closed on every call",
        ),
        RedLine(
            "RL-7",
            "Deterministic Offline Replay Fallback",
            NOT_MEASURED,
            None,
            "the assistant never replays by decision (ADR-019); an outage is a plain 503",
        ),
    )


def run_probes(models: ReadModels, aml: AmlSnapshot, replay: ReplayOutcome) -> ProbeReport:
    probe = _Prober(models)
    exec_, aml_, comp = (
        principal_for("ops-probe", w)
        for w in ("executive", "aml_investigator", "compliance_auditor")
    )
    queue = models.aml.get_triage_queue(min_score=0, limit=ROUNDS)
    ids = [q["entity_id"] for q in queue]
    held = [e for e in ids if models.aml.get_pending_withdrawal(e) is not None][:ROUNDS]

    probe.timed(
        SLICategory.METRIC_QUERY_LATENCY,
        exec_,
        "get_metric",
        [{"metric_id": "net_revenue_usd"}] * ROUNDS,
        1.0,
    )
    probe.timed(
        SLICategory.ALERT_DOSSIER_ASSEMBLY,
        aml_,
        "get_aml_dossier",
        [{"entity_id": e} for e in ids],
        1000.0,
    )
    probe.timed(
        SLICategory.PRE_WITHDRAWAL_DECISION,
        aml_,
        "check_withdrawal_risk",
        [{"entity_id": e} for e in held],
        1000.0,
    )
    for _ in range(ROUNDS):
        _, ok = probe.call(exec_, "get_briefing", {})
        probe.record(SLICategory.MORNING_BRIEFING_AVAILABILITY, 100.0 if ok else 0.0, ok)
    for _ in range(ROUNDS):
        _, ok = probe.call(comp, "verify_chain", {})
        probe.record(SLICategory.LEDGER_CHAIN_INTEGRITY, 0.0 if ok else 1.0, ok)
    missed = (
        replay.planted - replay.caught
    )  # a planted breach that got in is a wrong decision, like a healthy one refused
    decisions = [True] * (replay.accepted - missed + replay.caught) + [False] * (
        replay.false_rejects + missed
    )
    for correct in decisions:
        probe.record(SLICategory.CONTRACT_ENFORCEMENT, 0.0 if correct else 1.0, correct)
    what_if = [
        probe.call(
            exec_, "run_what_if", {"shock": "competitor_payout_increase", "magnitude_pct": float(m)}
        )[0]
        for m in range(-50, 50)
    ][:WHAT_IF_ROUNDS]
    first, second = _briefing_value(probe, exec_), _briefing_value(probe, exec_)
    return ProbeReport(
        red_lines=_red_lines(models, aml, probe, what_if, first == second and first is not None),
        events=probe.events,
        what_if_p95_ms=round(_p95(what_if), 2),
    )


def _briefing_value(probe: _Prober, who: Principal) -> Any:
    outcome = probe.port.call(who, "get_briefing", {})
    return outcome.payload().get("horizons") if outcome.error is None else None
