"""Test foundational base models, serialization, and security markings (T006)."""

from eios.ontology.config import SecurityMarking
from eios.ontology.core.base import OntologyLink, OntologyObject
from eios.ontology.core.interfaces import TransactingEntity


class MockClient(OntologyObject):
    client_id: str
    lifetime_value: float = 0.0

    @property
    def primary_key(self) -> str:
        return self.client_id


class MockCase(OntologyObject):
    case_id: str
    status: str = "OPEN"

    @property
    def primary_key(self) -> str:
        return self.case_id


def test_ontology_object_instantiation_and_markings():
    client = MockClient(
        client_id="C-1001",
        lifetime_value=12500.50,
        markings=[SecurityMarking.PII],
    )
    assert client.primary_key == "C-1001"
    assert SecurityMarking.PII in client.markings
    assert client.has_marking(SecurityMarking.PII)
    assert not client.has_marking(SecurityMarking.SENSITIVE_COMPLIANCE)


def test_ontology_object_serialization():
    case = MockCase(
        case_id="CASE-900",
        markings=[SecurityMarking.SENSITIVE_COMPLIANCE],
    )
    dumped = case.to_dict()
    assert dumped["case_id"] == "CASE-900"
    assert dumped["markings"] == ["SENSITIVE_COMPLIANCE"]


def test_ontology_link_instantiation():
    link = OntologyLink(
        link_type="USES_DEVICE",
        source_id="C-1001",
        target_id="DEV-88",
        cardinality="MANY_TO_MANY",
        metadata={"session_count": 12},
    )
    assert link.link_type == "USES_DEVICE"
    assert link.source_id == "C-1001"
    assert link.target_id == "DEV-88"
    assert link.metadata["session_count"] == 12


def test_polymorphic_interfaces_isinstance_check():
    class ValidTransactingClient(MockClient, TransactingEntity):
        def get_total_volume(self, window: str = "30d") -> float:
            return 50000.0

        def get_net_flow(self, window: str = "30d") -> float:
            return 12000.0

        def get_risk_rating(self) -> str:
            return "LOW"

    obj = ValidTransactingClient(client_id="C-200")
    assert isinstance(obj, TransactingEntity)
    assert obj.get_total_volume() == 50000.0
    assert obj.get_net_flow() == 12000.0
    assert obj.get_risk_rating() == "LOW"
