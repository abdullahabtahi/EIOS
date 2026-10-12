"""Gateway request, response and trace models (frozen; invariants enforced at construction)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Any

from pydantic import AwareDatetime, Field, field_validator, model_validator

from eios.common.untrusted_text import UntrustedText
from eios.common.validation import StrictModel

NonEmptyStr = Annotated[str, Field(min_length=1)]
Count = Annotated[int, Field(strict=True, ge=0)]
Cost = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Outcome(StrEnum):
    OK = "ok"
    REPLAY = "replay"
    UNAVAILABLE = "unavailable"
    CAP_REACHED = "cap_reached"


class GatewayRequest(StrictModel):
    """A call to the gateway. It has no model, price or provider field by design (FR-022).

    ``inputs`` values are plain strings (trusted template slots) or wrapped ``UntrustedText``
    (``{{untrusted:name}}`` slots); which is which is checked against the locked template.
    """

    prompt_id: NonEmptyStr
    prompt_version: NonEmptyStr
    inputs: Mapping[str, Any]
    correlation_id: NonEmptyStr
    caller: NonEmptyStr

    @field_validator("inputs", mode="after")
    @classmethod
    def _freeze_inputs(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        for item in value.values():
            if not isinstance(item, str | UntrustedText):
                raise ValueError("input values must be str or UntrustedText")
        return MappingProxyType(dict(value))


class GatewayResponse(StrictModel):
    """Text only. Business numbers come from deterministic tools, never from this response."""

    outcome: Outcome
    content: str | None
    trace_id: NonEmptyStr
    replay_original_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def _check_outcome_fields(self) -> GatewayResponse:
        has_text = self.outcome in (Outcome.OK, Outcome.REPLAY)
        if has_text != (self.content is not None):
            raise ValueError("content is present exactly for ok and replay outcomes")
        if (self.outcome is Outcome.REPLAY) != (self.replay_original_at is not None):
            raise ValueError("replay_original_at is present exactly for the replay outcome")
        return self


class CallMeasure(StrictModel):
    """What one call consumed; cost is derived from configured prices, null without prices."""

    tokens_in: Count
    tokens_out: Count
    latency_ms: Count
    cost: Cost | None


def _iso_utc(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    precision = "microseconds" if utc.microsecond else "seconds"
    return utc.isoformat(timespec=precision).replace("+00:00", "Z")


class LLMCallTrace(StrictModel):
    """One record per call, conforming to ``schemas/llm-call-trace.schema.json``."""

    trace_id: NonEmptyStr
    correlation_id: NonEmptyStr
    prompt_id: NonEmptyStr
    prompt_version: NonEmptyStr
    config_identity: NonEmptyStr
    tokens_in: Count
    tokens_out: Count
    cost: Cost | None
    latency_ms: Count
    outcome: Outcome
    replay_original_at: AwareDatetime | None = None
    recorded_at: AwareDatetime

    @model_validator(mode="after")
    def _check_replay_timestamp(self) -> LLMCallTrace:
        if (self.outcome is Outcome.REPLAY) != (self.replay_original_at is not None):
            raise ValueError("replay_original_at is present exactly for the replay outcome")
        return self

    def to_record(self) -> dict[str, object]:
        """Schema-shaped dict; ``replay_original_at`` appears only for replays."""
        record: dict[str, object] = {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "config_identity": self.config_identity,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "outcome": self.outcome.value,
            "recorded_at": _iso_utc(self.recorded_at),
        }
        if self.replay_original_at is not None:
            record["replay_original_at"] = _iso_utc(self.replay_original_at)
        return record
