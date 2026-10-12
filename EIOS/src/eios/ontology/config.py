"""Configuration and security marking definitions for EIOS Layer 2 Ontology."""

from enum import StrEnum

from pydantic import BaseModel


class SecurityMarking(StrEnum):
    """Mandatory security markings per docs/data_products_and_omcp.md and docs/foundry.md."""

    PII = "PII"
    SENSITIVE_COMPLIANCE = "SENSITIVE_COMPLIANCE"
    PARTNER_COMMERCIAL = "PARTNER_COMMERCIAL"


class OntologyConfig(BaseModel):
    """Runtime configuration for Ontology, Metric Registry, Graph, and Action Intent Hub."""

    hot_state_db_path: str = ":memory:"
    hub_degree_threshold: int = 5
    action_token_expiry_minutes: int = 15
    auditor_relative_tolerance: float = 0.01  # 1% relative tolerance
    kms_key_id: str = (
        "projects/eios-enterprise/locations/global/keyRings/eios-ring/"
        "cryptoKeys/action-intent-signer/cryptoKeyVersions/1"
    )
    use_local_kms_mock: bool = True
    graph_rebuild_batch_size: int = 50000
