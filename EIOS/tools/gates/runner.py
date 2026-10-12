"""Gate and suite runner: run-all-then-fail, every outcome on a schema-valid run record.

Two entry points share one finishing path: ``run_gates`` (rows of config/gates.yaml, commands
run from the target repo root) and ``run_suites`` (evals/registry.yaml entries filtered by the
tier-by-workflow matrix). A missing or non-executable command, a timeout and a missing report
are failures, never skips. Skipping exists only as ``skipped_with_reason``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date
from pathlib import Path

from eios.common.errors import ToolError
from tools.gates.commit_ref import compute_commit_ref
from tools.gates.gate_config import GateSpec
from tools.gates.process import build_env, run_commands
from tools.gates.quarantine import QuarantineEntry, partition
from tools.gates.registry import SuiteEntry, Tier, tier_runs_in
from tools.gates.run_record import (
    Clock,
    GateResult,
    Outcome,
    PipelineRunRecord,
    RunState,
    SystemClock,
    Workflow,
    new_record,
    write_record,
)

DEFAULT_TIMEOUT_SECONDS = 900.0  # [ASSUMPTION] per-gate wall-clock ceiling
GATE_LOG_DIR = Path("evals") / "reports" / "gates"
SUITE_LOG_DIR = Path("evals") / "reports" / "suites"
REPORTS_DIR = Path("evals") / "reports"
EXPIRED_PREFIX = "quarantine_expired"

ResultCallback = Callable[[GateResult], None]


def default_tool_root() -> Path:
    """The repository that holds ``tools/``, ``evals/``, ``src/`` and the schemas."""
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class RunSettings:
    """Where and how a run executes. ``repo_root`` is the target (cwd for commands)."""

    repo_root: Path
    tool_root: Path = field(default_factory=default_tool_root)
    workflow: Workflow = Workflow.PR
    clock: Clock = field(default_factory=SystemClock)
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    sbom_ref: str | None = None
    commit_ref: str | None = None
    persist: bool = True


@dataclass(frozen=True, slots=True)
class RunOutcome:
    record: PipelineRunRecord
    record_path: Path | None
    quarantined_count: int
    messages: tuple[str, ...] = ()

    @property
    def exit_code(self) -> int:
        return 0 if self.record.state is RunState.PASSED else 1


# --- shared helpers -----------------------------------------------------------------------


def _begin(settings: RunSettings) -> PipelineRunRecord:
    commit_ref = settings.commit_ref or compute_commit_ref(settings.repo_root)
    record = new_record(settings.workflow, commit_ref, settings.clock).start_gates()
    return record.with_sbom_ref(settings.sbom_ref) if settings.sbom_ref else record


def _finish(
    record: PipelineRunRecord, settings: RunSettings, quarantined: int, messages: Sequence[str]
) -> RunOutcome:
    finished = record.finish(settings.clock.now())
    path = (
        write_record(finished, settings.repo_root, settings.tool_root) if settings.persist else None
    )
    return RunOutcome(finished, path, quarantined, tuple(messages))


def _write_log(repo_root: Path, directory: Path, name: str, text: str) -> str:
    """Write ``text`` to ``<directory>/<name>.log`` in the target repo; return the relative ref."""
    relative = directory / f"{name}.log"
    target = repo_root / relative
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise ToolError(f"could not write log {target}: {exc}") from exc
    return relative.as_posix()


def _append(
    record: PipelineRunRecord, result: GateResult, on_result: ResultCallback | None
) -> PipelineRunRecord:
    if on_result is not None:
        on_result(result)
    return record.with_result(result)


def _today(settings: RunSettings) -> date:
    return settings.clock.now().astimezone(UTC).date()


# --- gates --------------------------------------------------------------------------------


def _skipped_by_quarantine(entry: QuarantineEntry, count: int) -> GateResult:
    reason = (
        f"quarantine: owner={entry.owner} expires={entry.expires.isoformat()} "
        f"reason={entry.reason} ({count} quarantined gates in this run)"
    )
    return GateResult(gate_id=entry.gate_id, outcome=Outcome.SKIPPED_WITH_REASON, reason=reason)


def _expired_result(entry: QuarantineEntry) -> GateResult:
    reason = (
        f"quarantine for gate {entry.gate_id} expired on {entry.expires.isoformat()} "
        f"(owner={entry.owner}); fix the gate or renew the entry"
    )
    return GateResult(
        gate_id=f"{EXPIRED_PREFIX}:{entry.gate_id}", outcome=Outcome.FAIL, reason=reason
    )


def _execute_gate(gate: GateSpec, settings: RunSettings) -> GateResult:
    result = run_commands(
        gate.command,
        cwd=settings.repo_root,
        env=build_env(settings.tool_root),
        timeout=settings.timeout_seconds,
        threshold=gate.threshold,
    )
    log_ref = _write_log(settings.repo_root, GATE_LOG_DIR, gate.id, result.log)
    outcome = Outcome.PASS if result.passed else Outcome.FAIL
    reason = None if result.passed else f"gate command failed; see {log_ref}"
    return GateResult(gate_id=gate.id, outcome=outcome, reason=reason, report_ref=log_ref)


def run_gates(
    gates: Iterable[GateSpec],
    settings: RunSettings,
    quarantine: Sequence[QuarantineEntry] = (),
    on_result: ResultCallback | None = None,
) -> RunOutcome:
    """Run ``gates`` in order. One failing gate never stops the rest; the run then ends failed."""
    selected = tuple(gates)
    ids = {g.id for g in selected}
    active, expired = partition([e for e in quarantine if e.gate_id in ids], _today(settings))
    quarantined = {e.gate_id: e for e in active}
    record = _begin(settings)
    for gate in selected:
        entry = quarantined.get(gate.id)
        result = (
            _skipped_by_quarantine(entry, len(active))
            if entry is not None
            else _execute_gate(gate, settings)
        )
        record = _append(record, result, on_result)
    for entry in expired:
        record = _append(record, _expired_result(entry), on_result)
    return _finish(record, settings, len(active), ())


# --- suites -------------------------------------------------------------------------------


def _suite_report_is_safe(settings: RunSettings, entry: SuiteEntry) -> bool:
    reports = (settings.repo_root / REPORTS_DIR).resolve()
    return (settings.repo_root / entry.report).resolve().is_relative_to(reports)


def _execute_suite(entry: SuiteEntry, settings: RunSettings) -> GateResult:
    report = settings.repo_root / entry.report
    if not _suite_report_is_safe(settings, entry):
        escape = f"report path escapes evals/reports/: {entry.report}"
        return GateResult(gate_id=entry.id, outcome=Outcome.FAIL, reason=escape)
    report.unlink(missing_ok=True)  # a stale report from an earlier run must not count
    report.parent.mkdir(parents=True, exist_ok=True)
    result = run_commands(
        [entry.command],
        cwd=settings.repo_root,
        env=build_env(settings.tool_root),
        timeout=settings.timeout_seconds,
    )
    log_ref = _write_log(settings.repo_root, SUITE_LOG_DIR, entry.id, result.log)
    reason: str | None = None
    if not result.passed:
        reason = f"suite command failed; see {log_ref}"
    elif not report.is_file():
        reason = f"suite did not produce its report: {entry.report}"
    outcome = Outcome.PASS if reason is None else Outcome.FAIL
    return GateResult(gate_id=entry.id, outcome=outcome, reason=reason, report_ref=entry.report)


def _skipped_by_matrix(entry: SuiteEntry, workflow: Workflow) -> GateResult:
    reason = f"tier {entry.tier.value} does not run under workflow {workflow.value}"
    return GateResult(
        gate_id=entry.id,
        outcome=Outcome.SKIPPED_WITH_REASON,
        reason=reason,
        report_ref=entry.report,
    )


def _check_requested_tiers(tiers: frozenset[Tier] | None, workflow: Workflow) -> None:
    for tier in sorted(tiers or (), key=lambda t: t.value):
        if not tier_runs_in(tier, workflow):
            raise ToolError(f"tier {tier.value} does not run under workflow {workflow.value}")


def _suite_messages(
    entries: Sequence[SuiteEntry], tiers: frozenset[Tier] | None, executed: int
) -> tuple[str, ...]:
    if not entries:
        return ("no suites registered",)
    if executed:
        return ()
    if tiers is not None:
        names = ", ".join(sorted(t.value for t in tiers))
        return (f"no suites registered for tier {names}",)
    return ("no suites executed: every registered suite is outside this workflow's tiers",)


def run_suites(
    entries: Sequence[SuiteEntry],
    settings: RunSettings,
    tiers: frozenset[Tier] | None = None,
    on_result: ResultCallback | None = None,
) -> RunOutcome:
    """Run registered suites in registry order, restricted to ``tiers`` when given.

    Suites whose tier the workflow forbids (sealed outside release-candidate, validation under
    pr) are never executed; they are recorded as ``skipped_with_reason``.
    """
    _check_requested_tiers(tiers, settings.workflow)
    record = _begin(settings)
    executed = 0
    scoped = [e for e in entries if tiers is None or e.tier in tiers]
    for entry in scoped:
        if tier_runs_in(entry.tier, settings.workflow):
            result = _execute_suite(entry, settings)
            executed += 1
        else:
            result = _skipped_by_matrix(entry, settings.workflow)
        record = _append(record, result, on_result)
    messages = _suite_messages(scoped if tiers is None else entries, tiers, executed)
    return _finish(record, settings, 0, messages)


# --- output -------------------------------------------------------------------------------

_LABELS = {Outcome.PASS: "PASS", Outcome.FAIL: "FAIL", Outcome.SKIPPED_WITH_REASON: "SKIP"}


def format_result_line(result: GateResult) -> str:
    """One status line, for example ``PASS lint`` or ``FAIL types (see evals/...)``."""
    line = f"{_LABELS[result.outcome]} {result.gate_id}"
    if result.outcome is Outcome.PASS:
        return line
    detail = result.reason or result.report_ref
    return f"{line} ({detail})" if detail else line


def format_footer(outcome: RunOutcome, *, show_quarantine: bool = True) -> tuple[str, ...]:
    path = f" (record: {outcome.record_path})" if outcome.record_path else ""
    quarantine = (f"quarantined gates: {outcome.quarantined_count}",) if show_quarantine else ()
    return (
        *outcome.messages,
        *quarantine,
        f"run {outcome.record.run_id}: {outcome.record.state.value}{path}",
    )


def format_summary(outcome: RunOutcome) -> tuple[str, ...]:
    lines = tuple(format_result_line(r) for r in outcome.record.gate_results)
    return (*lines, *format_footer(outcome))
