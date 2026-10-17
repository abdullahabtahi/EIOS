"""The radar's score is a current disengagement risk, not a 30-day churn probability (see docs/operations-engine.md)."""

from eios.cockpit.partner_engine_view import _risk_section
from eios.dataplane.partner_engine import PartnerSnapshot
from eios.dataplane.partner_service import EnginePartnerService


def test_the_executive_briefing_does_not_call_the_score_a_30_day_probability(executive_service) -> None:  # type: ignore[no-untyped-def]
    headline = " ".join(
        h.headline for h in executive_service.get_morning_briefing().horizons if h.horizon_name == "Partner"
    )
    assert "disengagement risk" in headline
    assert "30-day churn hazard" not in headline


def test_the_partner_dossier_risk_section_says_what_the_score_is(
    partner_snapshot: PartnerSnapshot, partner_service: EnginePartnerService
) -> None:
    pid = str(partner_snapshot.scored.index[0])
    section = _risk_section(partner_service, pid, "2026-10-14T08:00:00+00:00")
    assert section["title"] == "Disengagement risk"
    text = section["narrative_text"]
    assert "disengagement risk" in text.lower()
    assert "churn hazard" not in text.lower()
    assert "30-day referred deposits" in text  # the volume window is unchanged


def test_the_partner_tool_description_names_the_score_without_a_forecast_claim() -> None:
    from eios.ontology.omcp.port.descriptions import DESCRIPTIONS

    text = DESCRIPTIONS["partner.signals"].lower()
    assert "disengagement risk" in text
    assert "churn hazard" not in text
