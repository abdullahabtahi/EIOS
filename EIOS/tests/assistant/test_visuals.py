"""Tables and charts in an answer: the model names a list a tool returned this turn, the platform draws it from that result."""

import asyncio
from typing import Any

from eios.assistant.config import AssistantSettings
from eios.assistant.scripted_model import call, draft
from eios.assistant.tools import expand_fact_ids
from eios.assistant.visuals import MAX_VISUALS, extract, sources_of
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import principal_for
from eios.ontology.omcp.port.readmodels import ReadModels

from .conftest import make_runtime

AML = principal_for("alice", "aml_investigator")
EXEC = principal_for("erin", "executive")
PORT = build_port(ReadModels.default())
TIMELINE = call("get_activity_timeline", entity_id="CR84920")
WHAT_IF = call("run_what_if", shock="competitor_spread_cut", magnitude_pct=10.0)


def _result(tool: str, args: dict[str, Any], who=AML) -> dict[str, Any]:
    outcome = PORT.call(who, tool, args)
    assert outcome.result is not None
    return outcome.payload()


def _sources(tool: str, args: dict[str, Any], who=AML) -> dict[str, dict[str, Any]]:
    raw = _result(tool, args, who)
    return sources_of(tool, raw, expand_fact_ids(raw))


def test_a_list_result_becomes_a_source_named_by_its_tool_and_field() -> None:
    raw = _result("get_activity_timeline", {"entity_id": "CR84920"})
    source = sources_of("get_activity_timeline", raw, expand_fact_ids(raw))[
        "get_activity_timeline.events"
    ]
    assert len(source["rows"]) == len(raw["events"]) > 1
    assert [c["key"] for c in source["columns"]][:2] == ["at", "kind"]
    assert source["rows"][0]["at"] == raw["events"][0]["at"]  # the value is the tool's, untouched
    assert source["data_origin"] == raw["data_origin"] and source["as_of"] == raw["as_of"]


def test_a_money_column_carries_its_unit_and_the_fact_id_of_each_cell() -> None:
    source = _sources("get_activity_timeline", {"entity_id": "CR84920"})[
        "get_activity_timeline.events"
    ]
    money = next(c for c in source["columns"] if c["key"] == "event_amount_usd")
    assert money["unit"] and money["kind"] == "number"
    with_amount = next(
        i for i, r in enumerate(source["rows"]) if r.get("event_amount_usd") is not None
    )
    assert source["fact_ids"][with_amount]["event_amount_usd"]


def test_no_more_columns_than_a_table_can_show() -> None:
    source = _sources("get_dq_board", {}, principal_for("dan", "data_operations"))[
        "get_dq_board.products"
    ]
    assert len(source["columns"]) <= 6


def test_a_result_marked_untrusted_offers_no_source() -> None:
    raw = {**_result("get_activity_timeline", {"entity_id": "CR84920"}), "untrusted": True}
    assert sources_of("get_activity_timeline", raw, expand_fact_ids(raw)) == {}


def test_a_table_the_model_names_is_returned_with_the_placeholder_taken_out() -> None:
    sources = _sources("get_activity_timeline", {"entity_id": "CR84920"})
    shown = extract(
        "Here is the activity. {{table:get_activity_timeline.events}} It is busy.", sources
    )
    assert shown.problems == ()
    assert shown.text == "Here is the activity. It is busy."
    assert [v.kind for v in shown.visuals] == ["table"]
    assert shown.visuals[0].source == "get_activity_timeline.events"


def test_a_source_no_tool_returned_is_a_problem_that_names_what_is_available() -> None:
    sources = _sources("get_activity_timeline", {"entity_id": "CR84920"})
    shown = extract("{{table:get_partner_signals.retention_deals}}", sources)
    assert shown.visuals == ()
    assert "get_partner_signals.retention_deals" in shown.problems[0]
    assert "get_activity_timeline.events" in shown.problems[0]


def test_a_chart_needs_a_category_axis_and_a_number_to_plot() -> None:
    sources = _sources(
        "run_what_if", {"shock": "competitor_spread_cut", "magnitude_pct": 10.0}, EXEC
    )
    shown = extract("{{chart:run_what_if.attribution}}", sources)
    chart = shown.visuals[0]
    assert (
        chart.chart is not None
        and chart.chart.x == "driver"
        and chart.chart.y == ("contribution_pct",)
    )
    assert chart.chart.type == "bar"  # a category axis, not a time axis


def test_a_time_axis_draws_a_line() -> None:
    sources = _sources("get_activity_timeline", {"entity_id": "CR84920"})
    shown = extract("{{chart:get_activity_timeline.events}}", sources)
    assert shown.visuals[0].chart is not None and shown.visuals[0].chart.type == "line"


def test_a_chart_of_a_list_with_nothing_to_plot_is_a_problem() -> None:
    sources = _sources("get_drill_status", {}, principal_for("dan", "data_operations"))
    shown = extract("{{chart:get_drill_status.runbooks}}", sources)
    assert shown.visuals == () and "table" in shown.problems[0]


def test_the_same_view_twice_is_one_and_the_most_is_bounded() -> None:
    sources = _sources("get_activity_timeline", {"entity_id": "CR84920"})
    sources |= _sources("list_alerts", {})
    twice = extract(
        "{{table:get_activity_timeline.events}} {{table:get_activity_timeline.events}}", sources
    )
    assert len(twice.visuals) == 1
    many = extract(
        "{{table:get_activity_timeline.events}} {{chart:get_activity_timeline.events}} {{table:list_alerts.alerts}}",
        sources,
    )
    assert len(many.visuals) == MAX_VISUALS


def test_a_turn_answers_with_a_chart_drawn_from_the_tool_result_not_from_the_draft() -> None:
    runtime, llm = make_runtime(
        [
            TIMELINE,
            draft("Activity picked up late in the window. {{chart:get_activity_timeline.events}}"),
        ]
    )
    out = asyncio.run(
        runtime.run_turn(principal=AML, question="chart the activity", entity_id="CR84920")
    )
    assert out.status == "ok" and out.answer.attempts == 1
    chart = out.answer.visuals[0]
    raw = _result("get_activity_timeline", {"entity_id": "CR84920"})
    assert [r["at"] for r in chart.rows] == [e["at"] for e in raw["events"]]
    assert "{{" not in out.answer.text
    responses = [
        part.function_response.response
        for content in llm.seen[-1].contents
        for part in content.parts or []
        if part.function_response
    ]
    assert responses[0]["visual_sources"] == [
        "get_activity_timeline.events"
    ]  # the model is told the name to write


def test_a_draft_that_names_a_list_nothing_returned_is_sent_back() -> None:
    runtime, _ = make_runtime(
        [
            TIMELINE,
            draft("{{table:get_activity_timeline.nope}} A table."),
            draft("No table is shown."),
        ]
    )
    out = asyncio.run(runtime.run_turn(principal=AML, question="table please", entity_id="CR84920"))
    assert out.answer.attempts == 2 and out.answer.visuals == ()


def test_a_view_survives_a_prefetched_tool() -> None:
    settings = AssistantSettings.from_env(
        {"EIOS_ENVIRONMENT": "test", "EIOS_ASSISTANT_PREFETCH": "1"}
    )
    runtime, _ = make_runtime(
        [draft("Horizons below. {{table:get_briefing.horizons}}")], settings=settings
    )
    out = asyncio.run(runtime.run_turn(principal=EXEC, question="Give me the morning briefing"))
    assert out.status == "ok" and out.steps[:1] == (
        "get_briefing",
    )  # the platform ran it, not the model
    assert [v.source for v in out.answer.visuals] == ["get_briefing.horizons"]
