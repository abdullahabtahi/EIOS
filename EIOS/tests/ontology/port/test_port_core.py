"""The port enforces scope, arguments, markings and the output contract where capabilities are served."""

from datetime import UTC, datetime
from typing import Any

import pytest

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.contracts import (
    DataOrigin,
    PortError,
    ToolErrorCode,
    ToolResult,
)
from eios.ontology.omcp.port.principal import Workstation, principal_for
from eios.ontology.omcp.port.registry import Handler, ToolSpec
from eios.ontology.omcp.port.service import GovernedToolPort, RefusalLog


class _Args(StrictModel):
    entity_id: str


class _Out(ToolResult):
    score: int


def _ok(_ctx: object, _who: object, args: _Args) -> _Out:
    return _Out(
        capability="aml.dossier",
        entity_id=args.entity_id,
        as_of=datetime(2026, 10, 14, tzinfo=UTC),
        data_origin=DataOrigin.FIXTURE,
        source="test",
        units={"score": "points"},
        score=7,
    )


def _missing(_ctx: object, _who: object, args: _Args) -> _Out:
    raise PortError(ToolErrorCode.NOT_FOUND, f"no entity {args.entity_id}")


def _wrong_type(_ctx: object, _who: object, args: _Args) -> ToolResult:
    return ToolResult(
        capability="aml.dossier",
        entity_id=None,
        as_of=datetime(2026, 10, 14, tzinfo=UTC),
        data_origin=DataOrigin.FIXTURE,
        source="t",
        units={},
    )


def _spec(name: str, handler: Handler = _ok, **over: Any) -> ToolSpec:
    base = dict(
        name=name,
        capability="aml.dossier",
        kind="evidence",
        workstations=(Workstation.AML_INVESTIGATOR,),
        args_model=_Args,
        result_model=_Out,
        handler=handler,
        budget_ms=300,
        markings=(),
    )
    return ToolSpec(**{**base, **over})


def _port(*specs: ToolSpec, log: RefusalLog | None = None) -> GovernedToolPort:
    return GovernedToolPort(specs, context=object(), refusals=log or RefusalLog())


AML = principal_for("u1", "aml_investigator")
PARTNER = principal_for("u1", "partner_manager")


def test_a_call_inside_the_role_returns_a_validated_result() -> None:
    outcome = _port(_spec("get_x")).call(AML, "get_x", {"entity_id": "CR1"})
    assert outcome.error is None and outcome.result is not None
    assert outcome.payload()["fact_ids"] == {"score": "aml.dossier:CR1:score"}


def test_list_tools_is_the_role_toolset_only() -> None:
    port = _port(_spec("get_x"), _spec("get_p", workstations=(Workstation.PARTNER_MANAGER,)))
    assert [t.name for t in port.list_tools(AML)] == ["get_x"]
    assert [t.name for t in port.list_tools(PARTNER)] == ["get_p"]


def test_out_of_role_call_is_refused_and_recorded() -> None:
    log = RefusalLog()
    outcome = _port(_spec("get_x"), log=log).call(PARTNER, "get_x", {"entity_id": "CR1"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.FORBIDDEN_ROLE
    assert [(r.uid, r.workstation, r.tool, r.code) for r in log.entries] == [
        ("u1", Workstation.PARTNER_MANAGER, "get_x", ToolErrorCode.FORBIDDEN_ROLE)
    ]


@pytest.mark.parametrize("name", ["approve_action", "execute_action", "nope"])
def test_a_tool_that_does_not_exist_is_refused_the_same_way(name: str) -> None:
    log = RefusalLog()
    outcome = _port(_spec("get_x"), log=log).call(AML, name, {})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.FORBIDDEN_ROLE
    assert len(log.entries) == 1


@pytest.mark.parametrize("args", [{}, {"entity_id": "CR1", "role": "admin"}, {"entity_id": 5}])
def test_invalid_arguments_are_typed_and_extra_fields_rejected(args: dict[str, object]) -> None:
    outcome = _port(_spec("get_x")).call(AML, "get_x", args)
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.INVALID_ARGUMENTS


def test_a_handler_error_is_returned_typed() -> None:
    outcome = _port(_spec("get_x", handler=_missing)).call(AML, "get_x", {"entity_id": "CR1"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.NOT_FOUND
    assert outcome.result is None


def test_output_must_match_the_declared_contract() -> None:
    outcome = _port(_spec("get_x", handler=_wrong_type)).call(AML, "get_x", {"entity_id": "CR1"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_a_marking_the_workstation_lacks_is_forbidden_and_the_handler_never_runs() -> None:
    ran: list[int] = []

    def spy(ctx: object, who: object, args: _Args) -> _Out:
        ran.append(1)
        return _ok(ctx, who, args)

    spec = _spec(
        "get_x",
        handler=spy,
        workstations=(Workstation.DATA_OPERATIONS,),
        markings=(SecurityMarking.SENSITIVE_COMPLIANCE,),
    )
    ops = principal_for("u1", "data_operations")
    outcome = _port(spec).call(ops, "get_x", {"entity_id": "CR1"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.FORBIDDEN_MARKING
    assert ran == []


def test_every_call_is_traced_with_tool_role_duration_and_status() -> None:
    port = _port(_spec("get_x"))
    port.call(AML, "get_x", {"entity_id": "CR1"})
    port.call(PARTNER, "get_x", {"entity_id": "CR1"})
    assert [(t.tool, t.workstation, t.status) for t in port.traces] == [
        ("get_x", Workstation.AML_INVESTIGATOR, "ok"),
        ("get_x", Workstation.PARTNER_MANAGER, ToolErrorCode.FORBIDDEN_ROLE.value),
    ]
    assert all(t.duration_ms >= 0 for t in port.traces)


def test_duplicate_tool_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="get_x"):
        _port(_spec("get_x"), _spec("get_x"))


def test_a_caller_supplied_tool_name_is_bounded_before_it_is_recorded() -> None:
    log = RefusalLog()
    nasty = "get_x\nINFO forged log line " + "x" * 500
    _port(_spec("get_x"), log=log).call(AML, nasty, {})
    stored = log.entries[0].tool
    assert "\n" not in stored and len(stored) <= 64
