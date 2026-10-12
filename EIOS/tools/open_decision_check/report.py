"""What the tool reports besides findings: each decision open or lifted, and what it skipped."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from eios.common.errors import EiosError
from tools.open_decision_check.config import Decision, OpenDecisionsConfig
from tools.records.index import DEFAULT_SOURCE, parse_adr_index

OPEN = "open"
LIFTED = "lifted"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class DecisionState:
    """One decision: ``open`` or ``lifted`` (config lift AND the index at the required status)."""

    adr: str
    state: str
    index_status: str  # the status the ADR index shows, or ``unavailable``
    config_lifted: bool


def _index_statuses(repo_root: Path) -> Mapping[str, str]:
    """ADR id to index status; empty when the index cannot be read (the report says so)."""
    try:
        text = (repo_root / DEFAULT_SOURCE).read_text(encoding="utf-8")
        return {row.adr_id: row.status for row in parse_adr_index(text, DEFAULT_SOURCE)}
    except OSError, UnicodeDecodeError, EiosError:
        return {}


def _state(decision: Decision, statuses: Mapping[str, str]) -> DecisionState:
    status = statuses.get(decision.adr, UNAVAILABLE)
    lifted = decision.lift.lifted and status == decision.lift.adr_status
    return DecisionState(decision.adr, LIFTED if lifted else OPEN, status, decision.lift.lifted)


def decision_states(repo_root: Path, config: OpenDecisionsConfig) -> tuple[DecisionState, ...]:
    statuses = _index_statuses(repo_root)
    return tuple(_state(decision, statuses) for decision in config.decisions)


def state_line(state: DecisionState) -> str:
    note = (
        "; config lifts it but the index does not allow it"
        if (state.state == OPEN and state.config_lifted)
        else ""
    )
    return f"{state.adr}: {state.state} (index status {state.index_status}{note})"


def report_extra(
    config: OpenDecisionsConfig, states: Sequence[DecisionState]
) -> Mapping[str, object]:
    """Report fields: per-decision state and the prototype paths excluded by configuration."""
    return {
        "decisions": {s.adr: {"state": s.state, "index_status": s.index_status} for s in states},
        "excluded_prototype_paths": list(config.scan.prototype_paths),
    }
