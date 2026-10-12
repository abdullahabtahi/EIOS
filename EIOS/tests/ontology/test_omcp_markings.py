"""Test OMCP server-side security marking enforcement and property redaction (T042)."""

import pytest

from eios.ontology.config import SecurityMarking
from eios.ontology.core.objects import Case, ClientAccount, Partner
from eios.ontology.omcp.markings import InsufficientMarkingError, SecurityMarkingEnforcer


def test_public_role_redacts_sensitive_compliance():
    enforcer = SecurityMarkingEnforcer(caller_role="PublicAgent")
    case = Case(
        case_id="CASE-1",
        target_id="C-1001",
        typology="MIRROR_TRADING",
        markings=[SecurityMarking.SENSITIVE_COMPLIANCE],
    )

    with pytest.raises(InsufficientMarkingError):
        enforcer.filter_entity(case)


def test_compliance_role_accesses_case_with_redacted_pii():
    enforcer = SecurityMarkingEnforcer(caller_role="AMLInvestigator")
    client = ClientAccount(
        client_id="C-1001",
        kyc_status="APPROVED",
        lifetime_value_usd=12000.0,
        markings=[SecurityMarking.PII],
    )

    filtered = enforcer.filter_entity(client)
    # PII markings must be retained or indicated, client_id token preserved
    assert filtered["client_id"] == "C-1001"
    assert "PII" in filtered["markings"]


def test_partner_commercial_marking_filtering():
    partner = Partner(
        partner_id="P-101",
        tier="TIER_1",
        value_at_risk_usd=90000.0,
        markings=[SecurityMarking.PARTNER_COMMERCIAL],
    )

    # Public agent cannot view PARTNER_COMMERCIAL
    public_enforcer = SecurityMarkingEnforcer(caller_role="PublicAgent")
    with pytest.raises(InsufficientMarkingError):
        public_enforcer.filter_entity(partner)

    # Partner manager can access
    pm_enforcer = SecurityMarkingEnforcer(caller_role="PartnerManager")
    filtered = pm_enforcer.filter_entity(partner)
    assert filtered["partner_id"] == "P-101"
