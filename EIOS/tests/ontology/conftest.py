"""Shared pytest fixtures for Layer 2 Ontology tests."""

from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from eios.contracts.base import DataProductEnum
from eios.ingestion.hot_state import HotStateEngine


@pytest.fixture
def mock_ec_key_pair():
    """Generate an in-memory ECDSA P-256 key pair simulating Cloud KMS."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture
def seeded_hot_state():
    """HotStateEngine populated with deterministic synthetic test records."""
    engine = HotStateEngine(db_path=":memory:")

    # Seed client_360
    for i in range(1, 21):
        engine.insert_event(
            DataProductEnum.CLIENT_360,
            {
                "client_id": f"C-{1000 + i}",
                "tax_id": f"TAX-{i}",
                "full_name": f"Trader {i}",
                "email": f"trader{i}@example.com",
                "phone": f"+1555000{i:04d}",
                "dob": "1990-01-01",
                "country": "CYP",
                "kyc_status": "APPROVED",
                "kyc_approved_at": datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
                "partner_id": f"P-{100 + (i % 3)}",
                "declared_monthly_income": 5000.0,
                "lifetime_value": 1500.0 * i,
                "segment": "VIP" if i > 15 else "STANDARD",
            },
        )

    # Seed partner_360
    for p in range(1, 4):
        engine.insert_event(
            DataProductEnum.PARTNER_360,
            {
                "partner_id": f"P-{100 + p}",
                "tier": "TIER_1" if p == 1 else "TIER_2",
                "region": "LATAM" if p == 1 else "EMEA",
                "tenure_months": 24 * p,
                "value_at_risk": 50000.0 * p,
                "manager_id": f"MGR-{p}",
                "status": "ACTIVE",
            },
        )

    # Seed transactions_aml
    for i in range(1, 31):
        is_deposit = i % 3 != 0
        engine.insert_event(
            DataProductEnum.TRANSACTIONS_AML,
            {
                "txn_id": f"TXN-{i}",
                "client_id": f"C-{1000 + (i % 10) + 1}",
                "txn_type": "deposit" if is_deposit else "withdrawal",
                "amount": 250.0 * i,
                "currency": "USD",
                "payment_method_id": f"PM-{(i % 4) + 1}",
                "payment_agent_id": None,
                "timestamp": datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC),
                "is_first_deposit": (i <= 10 and is_deposit),
                "status": "SETTLED",
            },
        )

    # Seed device_network_graph: connect C-1001 through C-1006 to a shared device (DEV-HUB)
    # to test Hub Suppression (degree 6 >= 5)
    for c in range(1, 7):
        engine.insert_event(
            DataProductEnum.DEVICE_NETWORK_GRAPH,
            {
                "edge_id": f"EDGE-DEV-{c}",
                "source_id": f"C-{1000 + c}",
                "target_id": "DEV-HUB",
                "edge_type": "USES_DEVICE",
                "first_seen": datetime(2026, 9, 1, tzinfo=UTC),
                "last_seen": datetime(2026, 10, 1, tzinfo=UTC),
                "session_count": 15,
                "is_shared_context": True,
            },
        )

    # Connect C-1011, C-1012, C-1013 in a tight collusion clique (DEV-RING-1)
    for c in [11, 12, 13]:
        engine.insert_event(
            DataProductEnum.DEVICE_NETWORK_GRAPH,
            {
                "edge_id": f"EDGE-RING-{c}",
                "source_id": f"C-{1000 + c}",
                "target_id": "DEV-RING-1",
                "edge_type": "USES_DEVICE",
                "first_seen": datetime(2026, 9, 1, tzinfo=UTC),
                "last_seen": datetime(2026, 10, 1, tzinfo=UTC),
                "session_count": 25,
                "is_shared_context": False,
            },
        )

    yield engine
    engine.close()


@pytest.fixture
def sample_tool_trace():
    """Realistic OMCP tool execution traces for Auditor Gate verification."""
    return [
        {
            "tool_name": "get_metric",
            "inputs": {"metric_id": "net_deposit_volume_usd", "filters": {"region": "LATAM"}},
            "output": {
                "metric_id": "net_deposit_volume_usd",
                "value": 142500.0,
                "unit": "USD",
                "as_of": "2026-10-05T12:00:00Z",
            },
        },
        {
            "tool_name": "get_metric",
            "inputs": {"metric_id": "ftd_count_28d"},
            "output": {
                "metric_id": "ftd_count_28d",
                "value": 38.0,
                "unit": "count",
                "as_of": "2026-10-05T12:00:00Z",
            },
        },
        {
            "tool_name": "get_partner_signals",
            "inputs": {"partner_id": "P-101"},
            "output": {
                "partner_id": "P-101",
                "churn_hazard_score": 0.28,
                "signals": [],
            },
        },
    ]


@pytest.fixture
def mock_kms_signer():
    """KMSActionSigner instance with local SECP256R1 keypair."""
    from eios.ontology.actions.signer import KMSActionSigner

    return KMSActionSigner(key_id="test-mock-kms-p256")


@pytest.fixture
def governance_hot_state():
    """HotStateEngine instance with governance tables initialized."""
    from eios.ingestion.hot_state import HotStateEngine

    return HotStateEngine(db_path=":memory:")


@pytest.fixture
def sample_action_intent_payload():
    """Sample valid ActionIntentToken payload dictionary."""
    return {
        "intent_id": "550e8400-e29b-41d4-a716-446655440000",
        "action_type": "HoldWithdrawal",
        "parameters": {"txn_id": "TXN-101", "reason": "VELOCITY_SPIKE"},
        "evidence_refs": ["EVID-1", "ALERT-99"],
        "severity": "HIGH",
        "status": "PENDING",
        "nonce": "a1b2c3d4e5f6789012345678abcdef01",
        "issued_at": "2026-10-08T08:00:00Z",
        "expires_at": "2026-10-08T08:15:00Z",
        "requester_agent_id": "SentinelAMLSpecialist",
        "kms_key_id": "test-mock-kms-p256",
        "signature": "MEQCIBZ...",
        "approvals": [],
        "propensity_score": 0.85,
        "causal_context": {"velocity": 4.2},
        "requires_dual_approval": True,
        "policy_tags": ["DUAL_APPROVAL_MANDATORY"],
    }

