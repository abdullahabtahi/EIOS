"""Partner capabilities and proposals: the screen's numbers, one identity, honest gaps (spec 023 US3)."""

import json
from typing import Any

import pytest

from eios.cockpit.partner import PartnerWorkstationService
from eios.ontology.omcp.port.contracts import ToolErrorCode
from eios.ontology.omcp.port.principal import Principal
from eios.ontology.omcp.port.proposals import KIND_TO_HUB_ACTION
from eios.ontology.omcp.port.service import GovernedToolPort
from tests.ontology.port.conftest import who

PARTNER = who("partner_manager")
AML = who("aml_investigator")


def _ok(
    port: GovernedToolPort, principal: Principal, tool: str, args: dict[str, Any]
) -> dict[str, Any]:
    outcome = port.call(principal, tool, args)
    assert outcome.error is None, outcome.error
    return outcome.payload()


def _radar(partner_id: str) -> dict[str, Any]:
    for p in PartnerWorkstationService().get_churn_radar_scatter().to_contract_dict()["partners"]:
        if p["partner_id"] == partner_id:
            return dict(p)
    raise AssertionError(partner_id)


@pytest.mark.parametrize("alias", ["PTR-882", "P-882", "AP-1029"])
def test_signals_equal_the_radar_for_every_alias(port: GovernedToolPort, alias: str) -> None:
    screen = _radar("PTR-882")
    got = _ok(port, PARTNER, "get_partner_signals", {"entity_id": alias})
    assert got["entity_id"] == "PTR-882"
    for field in (
        "churn_hazard_probability",
        "login_decay_pct",
        "ftd_decay_pct",
        "realized_volume_30d_usd",
        "primary_root_cause",
    ):
        assert got[field] == screen[field]
    assert got["churn_hazard_probability"] == 0.78 and got["login_decay_pct"] == -68.0


def test_signals_differ_per_partner_not_constants(port: GovernedToolPort) -> None:
    a = _ok(port, PARTNER, "get_partner_signals", {"entity_id": "PTR-882"})
    b = _ok(port, PARTNER, "get_partner_signals", {"entity_id": "PTR-104"})
    assert a["churn_hazard_probability"] != b["churn_hazard_probability"]
    assert b["churn_hazard_probability"] == _radar("PTR-104")["churn_hazard_probability"]


def test_unknown_partner_is_not_found_never_a_default(port: GovernedToolPort) -> None:
    out = port.call(PARTNER, "get_partner_signals", {"entity_id": "PTR-000"})
    assert out.error is not None and out.error.code is ToolErrorCode.NOT_FOUND


def test_an_account_is_not_a_partner(port: GovernedToolPort) -> None:
    out = port.call(PARTNER, "get_partner_signals", {"entity_id": "CR84920"})
    assert out.error is not None and out.error.code is ToolErrorCode.NOT_FOUND


def test_worklist_is_ranked_by_expected_loss(port: GovernedToolPort) -> None:
    got = _ok(port, PARTNER, "list_partner_worklist", {"limit": 5})
    losses = [p["expected_loss_usd"] for p in got["partners"]]
    assert losses == sorted(losses, reverse=True) and len(losses) == 5
    top = got["partners"][0]
    assert top["expected_loss_usd"] == round(
        top["churn_hazard_probability"] * top["realized_volume_30d_usd"], 2
    )
    assert got["units"]["partners[].expected_loss_usd"] == "USD"


def test_integrity_states_observed_facts_for_the_partner_with_evidence(
    port: GovernedToolPort,
) -> None:
    got = _ok(port, PARTNER, "get_partner_integrity", {"entity_id": "AP-1029"})
    assert got["entity_id"] == "PTR-882" and got["rings"]
    assert got["rings"][0]["unearned_commission_liability_usd"] == 42500.0
    text = json.dumps(got).lower()
    assert "fraud" not in text and "guilty" not in text and "accus" not in text
    assert "observed" in got["statement"].lower()


def test_integrity_without_evidence_is_unavailable_not_clean(port: GovernedToolPort) -> None:
    out = port.call(PARTNER, "get_partner_integrity", {"entity_id": "PTR-104"})
    assert out.error is not None and out.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_client_quality_is_unavailable_until_a_portfolio_feed_exists(
    port: GovernedToolPort,
) -> None:
    out = port.call(PARTNER, "get_client_quality", {"entity_id": "PTR-882"})
    assert out.error is not None and out.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_comms_are_untrusted_structured_first_and_bounded(port: GovernedToolPort) -> None:
    got = _ok(port, PARTNER, "read_partner_comms", {"entity_id": "PTR-882"})
    assert got["untrusted"] is True and got["messages"]
    keys = list(got)
    assert keys.index("messages") > keys.index("topic_counts")  # structured fields before excerpts
    for m in got["messages"]:
        assert m["untrusted"] is True and len(m["excerpt"]) <= 280


def test_proposal_is_readable_costed_ranged_and_stages_nothing(port: GovernedToolPort) -> None:
    signals = _ok(port, PARTNER, "get_partner_signals", {"entity_id": "PTR-882"})
    deal = signals["retention_deals"][0]
    got = _ok(
        port,
        PARTNER,
        "propose_partner_action",
        {"entity_id": "PTR-882", "playbook_id": deal["playbook_id"]},
    )
    assert got["label"] and got["offer"] and got["estimated_cost_usd"] == deal["estimated_cost_usd"]
    assert got["expected_effect_low"] < got["expected_effect_high"]
    assert got["approval_requirement"] and got["signed"] is False and got["staged"] is False
    text = json.dumps(got)
    for constant in set(KIND_TO_HUB_ACTION.values()) | {
        "DeployRetentionVIPDeal",
        "DEPLOY_RETENTION_PLAYBOOK",
    }:
        assert constant not in text


def test_a_deal_over_the_fast_path_budget_needs_four_eyes(port: GovernedToolPort) -> None:
    signals = _ok(port, PARTNER, "get_partner_signals", {"entity_id": "PTR-882"})
    big = max(signals["retention_deals"], key=lambda d: d["estimated_cost_usd"])
    got = _ok(
        port,
        PARTNER,
        "propose_partner_action",
        {"entity_id": "PTR-882", "playbook_id": big["playbook_id"]},
    )
    assert (
        "second" in got["approval_requirement"].lower()
        or "four" in got["approval_requirement"].lower()
    )


def test_proposal_for_an_unknown_deal_or_partner_is_refused(port: GovernedToolPort) -> None:
    assert (
        port.call(
            PARTNER, "propose_partner_action", {"entity_id": "PTR-882", "playbook_id": "pb_nope"}
        ).error
        is not None
    )
    out = port.call(
        PARTNER,
        "propose_partner_action",
        {"entity_id": "PTR-000", "playbook_id": "pb_vip_spread_deal"},
    )
    assert out.error is not None and out.error.code is ToolErrorCode.NOT_FOUND
    out = port.call(
        PARTNER,
        "propose_partner_action",
        {"entity_id": "PTR-104", "playbook_id": "pb_vip_spread_deal"},
    )
    assert out.error is not None and out.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_hold_proposal_comes_from_the_withdrawal_assessment(port: GovernedToolPort) -> None:
    got = _ok(port, AML, "propose_hold", {"entity_id": "CR84920"})
    assert (
        got["estimated_cost_usd"] == 0.0
        and got["expected_effect_low"] == got["expected_effect_high"] == 7800.0
    )
    assert got["units"]["expected_effect_low"] == "USD"
    assert (
        "four" in got["approval_requirement"].lower()
        or "second" in got["approval_requirement"].lower()
    )
    assert got["signed"] is False and got["staged"] is False


def test_action_kinds_map_to_the_intent_hubs_vocabulary() -> None:
    from eios.ontology.actions.intent_hub import CANONICAL_ACTION_SPECS

    assert set(KIND_TO_HUB_ACTION.values()) <= set(CANONICAL_ACTION_SPECS)
