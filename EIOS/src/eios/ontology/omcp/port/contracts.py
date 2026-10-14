"""Result envelope and typed errors for the governed tool port (spec 023 FR-002, FR-003).

A successful result keeps its domain fields flat at the top level (the agent gates address them by path,
for example `discrepancy_multiplier`) and adds the envelope: capability, entity, as-of, origin, source,
markings, the unit of every figure and a stable id for every figure. A figure with no unit is a defect, so
it fails validation instead of reaching an operator.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Self

from pydantic import Field, computed_field, field_validator, model_validator

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking


class DataOrigin(StrEnum):
    FIXTURE = "fixture"
    LIVE = "live"


class ToolErrorCode(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN_ROLE = "FORBIDDEN_ROLE"
    FORBIDDEN_MARKING = "FORBIDDEN_MARKING"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    STALE = "STALE"
    TIMEOUT = "TIMEOUT"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"


class ToolError(StrictModel):
    """A typed failure. Never an empty or default value in disguise."""

    code: ToolErrorCode
    message: str = Field(min_length=1)
    retryable: bool = False


class PortError(Exception):
    """Raised by a handler to return a typed error; the port converts it to `ToolError`."""

    def __init__(self, code: ToolErrorCode, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.error = ToolError(code=code, message=message, retryable=retryable)


ENVELOPE_FIELDS = frozenset(
    {"capability", "entity_id", "as_of", "data_origin", "source", "markings", "units", "untrusted"}
)


def leaf_paths(value: Any, prefix: str = "") -> dict[str, bool]:
    """Dotted path of every non-null leaf mapped to whether it is a figure (bool is not a figure).

    List items are written `name[]`, so one unit covers every item of a list.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        out: dict[str, bool] = {}
        for key, child in value.items():
            out |= leaf_paths(child, f"{prefix}.{key}" if prefix else str(key))
        return out
    if isinstance(value, list | tuple):
        out = {}
        for child in value:
            out |= leaf_paths(child, f"{prefix}[]")
        return out
    return {prefix: isinstance(value, int | float) and not isinstance(value, bool)}


class ToolResult(StrictModel):
    capability: str
    entity_id: str | None
    as_of: datetime
    data_origin: DataOrigin
    source: str = Field(min_length=1)
    markings: tuple[SecurityMarking, ...] = ()
    units: dict[str, str]
    untrusted: bool = False  # True when the result carries text that originated outside the system

    @field_validator("as_of")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    def domain_leaves(self) -> dict[str, bool]:
        body = {k: v for k, v in self.model_dump().items() if k not in ENVELOPE_FIELDS}
        body.pop("fact_ids", None)
        return leaf_paths(body)

    @model_validator(mode="after")
    def _every_figure_has_a_unit(self) -> Self:
        leaves = self.domain_leaves()
        figures = {path for path, is_figure in leaves.items() if is_figure}
        declared = set(self.units)
        if figures - declared:
            raise ValueError(f"figures without a unit: {sorted(figures - declared)}")
        text_fields = {path for path, is_figure in leaves.items() if not is_figure}
        if declared & text_fields:
            raise ValueError(
                f"units for fields that are not figures: {sorted(declared & text_fields)}"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fact_ids(self) -> dict[str, str]:
        return {
            path: f"{self.capability}:{self.entity_id or '-'}:{path}" for path in sorted(self.units)
        }
