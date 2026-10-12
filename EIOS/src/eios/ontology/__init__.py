"""EIOS Layer 2: Kinetic Ontology & Governed Semantic Metric Layer.

Provides four-fold integration: Data, Logic, Action, and Security.
- Metric Registry (ADR-003): Deterministic KPI queries over DuckDB hot state.
- Kinetic Ontology Core: 13 Object Types, 9 Link Types, and Polymorphic Interfaces.
- Property Graph (ADR-004, ADR-008): In-memory NetworkX graph with Hub Suppression.
- Deterministic Functions: Value-at-Risk, churn hazard, and syndicate scoring.
- Metric Auditor Gate: Egress firewall enforcing Principle I and Red-Line RL-1.
- Governed Action Intent Hub: Cloud KMS ECDSA P-256 signed action tokens (Principle II).
- OMCP Tool Surface: Model Context Protocol tools with security marking enforcement.
"""

from eios.ontology.config import OntologyConfig

__all__ = ["OntologyConfig"]
