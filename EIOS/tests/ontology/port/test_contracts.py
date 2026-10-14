"""The result envelope and typed errors (spec 023 FR-002, FR-003)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from eios.agent_gates.records import ToolErrorCode as RecordsErrorCode
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.contracts import (
    DataOrigin,
    ToolError,
    ToolErrorCode,
    ToolResult,
)

NOW = datetime(2026, 10, 14, tzinfo=UTC)


class _Sample(ToolResult):
    score: int
    ratio: float
    label: str


def _make(**over: object) -> _Sample:
    base: dict[str, object] = {
        "capability": "aml.dossier",
        "entity_id": "CR84920",
        "as_of": NOW,
        "data_origin": DataOrigin.FIXTURE,
        "source": "cockpit.aml",
        "markings": (SecurityMarking.PII,),
        "units": {"score": "points", "ratio": "multiplier"},
        "score": 89,
        "ratio": 16.0,
        "label": "x",
    }
    return _Sample.model_validate({**base, **over})


def test_every_figure_gets_a_stable_fact_id() -> None:
    result = _make()
    assert result.fact_ids == {
        "score": "aml.dossier:CR84920:score",
        "ratio": "aml.dossier:CR84920:ratio",
    }


def test_a_figure_without_a_unit_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ratio"):
        _make(units={"score": "points"})


def test_a_unit_for_a_field_that_is_not_a_figure_is_rejected() -> None:
    with pytest.raises(ValidationError, match="label"):
        _make(units={"score": "points", "ratio": "multiplier", "label": "text"})


def test_naive_as_of_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _make(as_of=datetime(2026, 10, 14))


def test_error_is_typed_and_never_empty() -> None:
    err = ToolError(code=ToolErrorCode.NOT_FOUND, message="no such account")
    assert err.code is ToolErrorCode.NOT_FOUND
    with pytest.raises(ValidationError):
        ToolError(code=ToolErrorCode.NOT_FOUND, message="")


def test_error_codes_are_a_superset_of_the_record_codes() -> None:
    assert {c.value for c in RecordsErrorCode} <= {c.value for c in ToolErrorCode} | {"OTHER"}
    assert {"FORBIDDEN_ROLE", "INVALID_ARGUMENTS"} <= {c.value for c in RecordsErrorCode}
