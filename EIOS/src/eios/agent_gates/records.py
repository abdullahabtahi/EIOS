"""The runtime-neutral Turn Record: one evaluated turn, the shared input of every gate (spec 022).

Contract: `specs/022-agent-quality-gates/contracts/turn-record.schema.json`. The judges in `core/` read the
JSON form of this record (`to_json_dict`), so they never import this module.
"""

from enum import StrEnum
from typing import Any, Self

from pydantic import Field, model_validator

from eios.common.validation import StrictModel


class Role(StrEnum):
    AML_INVESTIGATOR = "aml_investigator"
    PARTNER_MANAGER = "partner_manager"
    EXECUTIVE = "executive"
    COMPLIANCE_AUDITOR = "compliance_auditor"
    DATA_OPERATIONS = "data_operations"


class IdentitySource(StrEnum):
    VERIFIED_TOKEN = "verified_token"  # noqa: S105 - an identity-source label, not a credential
    REQUEST_BODY = "request_body"
    NONE = "none"


class DataOrigin(StrEnum):
    FIXTURE = "fixture"
    LIVE = "live"


class Outcome(StrEnum):
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"


class ToolErrorCode(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN_MARKING = "FORBIDDEN_MARKING"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    STALE = "STALE"
    TIMEOUT = "TIMEOUT"
    OTHER = "OTHER"


class ToolCall(StrictModel):
    name: str
    capability: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: ToolErrorCode | None = None
    latency_ms: float = Field(default=0.0, ge=0)
    untrusted: bool = False

    @model_validator(mode="after")
    def _result_xor_error(self) -> Self:
        if self.result is not None and self.error is not None:
            raise ValueError("a tool call carries a result or an error, not both")
        return self


class FactRef(StrictModel):
    tool_call_index: int = Field(ge=0)
    path: str


class Binding(StrictModel):
    """A reference answer's link from a span of text to the fact that produced it."""

    span: tuple[int, int]
    fact_ref: FactRef
    unit: str


class TurnRecord(StrictModel):
    record_id: str
    case_id: str | None = None
    repeat: int = Field(ge=0)
    runtime: str
    session_id: str
    turn_index: int = Field(ge=1)
    operator_id: str
    identity_source: IdentitySource
    role: Role
    entity_context: dict[str, Any] | None = None
    question: str
    tool_calls: list[ToolCall]
    rounds: int = Field(ge=0)
    answer: str
    bindings: list[Binding] | None = None
    citations: list[str] = Field(default_factory=list)
    is_replay_fallback: bool
    fallback_reason: str | None = None
    audit_verdict: str | None = None
    data_origin: DataOrigin
    latency_ms: float = Field(ge=0)
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)
    outcome: Outcome
    inconclusive_reason: str | None = None

    @model_validator(mode="after")
    def _reasons_are_present(self) -> Self:
        if self.is_replay_fallback and not self.fallback_reason:
            raise ValueError("a replay answer must carry a fallback_reason")
        if self.outcome is Outcome.INCONCLUSIVE and not self.inconclusive_reason:
            raise ValueError("an inconclusive turn must carry an inconclusive_reason")
        return self

    def to_json_dict(self) -> dict[str, Any]:
        """The JSON form the judges and the schema read."""
        return self.model_dump(mode="json")


def to_agents_cli_case(record: TurnRecord) -> dict[str, Any]:
    """The `agents-cli eval` case for a record (contract: contracts/agents-cli-trace-mapping.md).

    `responses` is required next to `agent_data`: without it every case errors in the Google grader.
    """
    agent = record.runtime
    events: list[dict[str, Any]] = [
        {"author": "user", "content": {"role": "user", "parts": [{"text": record.question}]}}
    ]
    for call in record.tool_calls:
        events.append(
            {
                "author": agent,
                "content": {
                    "role": "model",
                    "parts": [{"function_call": {"name": call.name, "args": call.arguments}}],
                },
            }
        )
        events.append(
            {
                "author": "tool",
                "content": {
                    "role": "user",
                    "parts": [
                        {
                            "function_response": {
                                "name": call.name,
                                "response": call.result or {"error": call.error},
                            }
                        }
                    ],
                },
            }
        )
    events.append(
        {"author": agent, "content": {"role": "model", "parts": [{"text": record.answer}]}}
    )
    return {
        "eval_case_id": record.record_id,
        "prompt": {"role": "user", "parts": [{"text": record.question}]},
        "responses": [{"response": {"role": "model", "parts": [{"text": record.answer}]}}],
        "agent_data": {
            "agents": {agent: {"agent_id": agent, "agent_type": "LlmAgent", "instruction": ""}},
            "turns": [{"turn_index": 0, "events": events}],
        },
        "data_origin": record.data_origin.value,
        "identity_source": record.identity_source.value,
        "is_replay_fallback": record.is_replay_fallback,
    }
