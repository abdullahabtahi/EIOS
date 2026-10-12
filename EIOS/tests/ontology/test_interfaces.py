"""Test polymorphic interface dispatch and hot-state hydrator (T017)."""

from datetime import UTC

from eios.ontology.core.hydrator import OntologyHydrator
from eios.ontology.core.interfaces import AuditableEntity, TransactingEntity
from eios.ontology.core.objects import Case, ClientAccount, Partner


def test_hydrator_client_account_implements_transacting_entity(seeded_hot_state):
    hydrator = OntologyHydrator(hot_state=seeded_hot_state)
    client = hydrator.hydrate_client("C-1001")

    assert isinstance(client, ClientAccount)
    assert isinstance(client, TransactingEntity)
    assert client.get_total_volume() >= 0.0
    assert client.get_net_flow() is not None
    assert client.get_risk_rating() in ["LOW", "MEDIUM", "HIGH"]


def test_hydrator_partner_implements_transacting_entity(seeded_hot_state):
    hydrator = OntologyHydrator(hot_state=seeded_hot_state)
    partner = hydrator.hydrate_partner("P-101")

    assert isinstance(partner, Partner)
    assert isinstance(partner, TransactingEntity)
    assert partner.get_total_volume() >= 0.0
    assert partner.get_risk_rating() in ["LOW", "MEDIUM", "HIGH"]


def test_hydrator_case_implements_auditable_entity(seeded_hot_state):
    # Insert a sample compliance case into hot state
    from datetime import datetime

    from eios.contracts.base import DataProductEnum

    seeded_hot_state.insert_event(
        DataProductEnum.COMPLIANCE_CASES,
        {
            "case_id": "CASE-101",
            "client_id": "C-1001",
            "status": "UNDER_INVESTIGATION",
            "typology": "MIRROR_TRADING",
            "analyst_id": "ANALYST-5",
            "risk_score": 0.88,
            "created_at": datetime(2026, 10, 1, tzinfo=UTC),
            "updated_at": datetime(2026, 10, 2, tzinfo=UTC),
        },
    )

    hydrator = OntologyHydrator(hot_state=seeded_hot_state)
    case = hydrator.hydrate_case("CASE-101")

    assert isinstance(case, Case)
    assert isinstance(case, AuditableEntity)
    assert len(case.get_audit_trail()) >= 1
    assert "SENSITIVE_COMPLIANCE" in case.get_security_markings()
