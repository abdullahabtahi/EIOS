"""The single entry point every suite uses to reach a runtime (spec 022 FR-003).

Contract: `specs/022-agent-quality-gates/contracts/agent-port.md`.
"""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any, Protocol

from pydantic import Field

from eios.agent_gates.records import (
    DataOrigin,
    IdentitySource,
    Outcome,
    Role,
    TurnRecord,
)
from eios.common.validation import StrictModel


class TurnRequest(StrictModel):
    question: str
    role: Role
    operator_id: str
    session_id: str
    turn_index: int = Field(default=1, ge=1)
    case_id: str | None = None
    entity_context: dict[str, Any] | None = None
    # Capability name to canned result, applied where the runtime dispatches tools (injection and failure cases).
    tool_fixtures: dict[str, dict[str, Any]] = Field(default_factory=dict)
    repeat: int = Field(default=0, ge=0)
    deadline_s: float = Field(default=60.0, gt=0)


class AgentPort(Protocol):
    runtime_name: str

    def run_turn(self, request: TurnRequest) -> TurnRecord: ...


def inconclusive_record(request: TurnRequest, runtime: str, reason: str) -> TurnRecord:
    """A complete record for a turn that could not be judged; it can never count as a pass."""
    return TurnRecord(
        record_id=f"{request.case_id or request.session_id}.{request.repeat}",
        case_id=request.case_id,
        repeat=request.repeat,
        runtime=runtime,
        session_id=request.session_id,
        turn_index=request.turn_index,
        operator_id=request.operator_id,
        identity_source=IdentitySource.NONE,
        role=request.role,
        entity_context=request.entity_context,
        question=request.question,
        tool_calls=[],
        rounds=0,
        answer="",
        is_replay_fallback=False,
        data_origin=DataOrigin.FIXTURE,
        latency_ms=0.0,
        outcome=Outcome.INCONCLUSIVE,
        inconclusive_reason=reason,
    )


def run_with_deadline(port: AgentPort, request: TurnRequest) -> TurnRecord:
    """Run one turn; a timeout or a crash becomes an inconclusive record, never an exception."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(port.run_turn, request).result(timeout=request.deadline_s)
    except FutureTimeout:
        reason = f"deadline of {request.deadline_s}s exceeded"
    except Exception as exc:  # any runtime failure must surface as inconclusive
        reason = f"{type(exc).__name__}: {exc}"
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return inconclusive_record(request, port.runtime_name, reason)
