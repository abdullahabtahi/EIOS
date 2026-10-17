"""Compliance and operations capabilities: read and explain, and never present absence of data as health."""

from typing import Any

from eios.assistant.tools import expand_fact_ids
from eios.cockpit.operations import DataPlatformOperationsService
from eios.hardening.runbooks import RunbookVerificationEngine
from eios.ingestion.circuit_breaker import IngestionCircuitBreaker
from eios.ontology.omcp.port.contracts import ToolErrorCode
from eios.ontology.omcp.port.principal import Principal
from eios.ontology.omcp.port.service import GovernedToolPort
from tests.ontology.port.conftest import who

AUDITOR = who("compliance_auditor")
OPS = who("data_operations")


def _ok(
    port: GovernedToolPort, principal: Principal, tool: str, args: dict[str, Any] | None = None
) -> dict[str, Any]:
    outcome = port.call(principal, tool, args or {})
    assert outcome.error is None, outcome.error
    return outcome.payload()


def test_ledger_timeline_is_ordered_and_bounded(port: GovernedToolPort) -> None:
    got = _ok(port, AUDITOR, "get_ledger_timeline", {"limit": 2})
    seqs = [e["ledger_seq"] for e in got["entries"]]
    assert seqs == sorted(seqs) and len(seqs) == 2
    assert got["units"]["entries[].ledger_seq"] == "sequence"
    too_many = port.call(AUDITOR, "get_ledger_timeline", {"limit": 5000})
    assert too_many.error is not None and too_many.error.code is ToolErrorCode.INVALID_ARGUMENTS


def test_intent_status_defaults_to_the_latest_and_hides_approver_identities(
    port: GovernedToolPort,
) -> None:
    got = _ok(port, AUDITOR, "get_intent_status")
    assert got["status"] and got["first_approver_role"] != got["second_approver_role"]
    flat = str(got).lower()
    assert "officer_" not in flat and "comment" not in flat
    missing = port.call(AUDITOR, "get_intent_status", {"intent_id": "intent_nope"})
    assert missing.error is not None and missing.error.code is ToolErrorCode.NOT_FOUND


def test_audit_status_reports_the_retention_checkpoint(port: GovernedToolPort) -> None:
    got = _ok(port, AUDITOR, "get_audit_status")
    assert got["is_immutable"] is True and got["compliance_lock_mode"] == "COMPLIANCE"
    assert got["units"]["chain_head_seq"] == "sequence"


def test_verify_chain_says_when_the_pass_is_simulated(port: GovernedToolPort) -> None:
    got = _ok(port, AUDITOR, "verify_chain")
    assert got["is_chain_unbroken"] is True
    assert got["is_simulated"] is True and got["data_origin"] == "fixture"
    assert got["total_entries_verified"] > 0


def test_dq_board_equals_the_screen_summary(port: GovernedToolPort) -> None:
    screen = DataPlatformOperationsService().get_board_summary()
    got = _ok(port, OPS, "get_dq_board")
    assert got["total_products"] == screen["total_products"]
    assert got["sla_compliance_rate_pct"] == screen["sla_compliance_rate_pct"]
    assert [p["product_name"] for p in got["products"]] == [
        p["product_name"] for p in screen["products"]
    ]


def test_dq_board_states_the_breach_budget_as_a_value_not_only_inside_an_alert_sentence(
    port: GovernedToolPort,
) -> None:
    """A model that explains a breach quotes the budget; a figure only inside a sentence cannot be shown, so the
    answer failed closed. The budget is a returned value, and the same one the engine judges breaches by."""
    got = _ok(port, OPS, "get_dq_board")
    assert got["breach_rate_budget"] == IngestionCircuitBreaker().breach_rate_threshold
    assert got["units"]["breach_rate_budget"] == "ratio"
    assert "breach_rate_budget" in expand_fact_ids(got)["fact_ids"]


def test_reliability_is_no_data_when_no_events_were_recorded_not_healthy(
    port: GovernedToolPort,
) -> None:
    got = _ok(port, OPS, "get_reliability")
    assert all(s["total_events"] == 0 for s in got["objectives"])
    assert got["overall_health"] == "NO_DATA"


def test_drill_status_is_the_runbook_catalogue_only(port: GovernedToolPort) -> None:
    got = _ok(port, OPS, "get_drill_status")
    assert got["registered_runbooks_count"] == len(
        RunbookVerificationEngine().get_runbook_catalog()
    )
    assert "no drill history" in got["scope"]


def test_calibration_needs_recorded_outcomes(port: GovernedToolPort) -> None:
    out = port.call(OPS, "get_calibration_status", {})
    assert out.error is not None and out.error.code is ToolErrorCode.DATA_UNAVAILABLE
