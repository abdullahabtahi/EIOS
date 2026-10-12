# ADR-004: Graph Engine (NetworkX with Hub Suppression & Parquet Warm-Start)

## Status

Accepted

## Date

2026-10-05

## Context

Financial crime rings, affiliate fraud rings, and smurfing syndicates operate across multi-hop relationships (devices, IP addresses, payment methods, parent/sub-affiliates).
Earlier proposals evaluated external graph databases (Neo4j, Spanner Graph). However, external clusters introduce cold-start latency, operational complexity, and network latency for real-time investigation traversals.
Additionally, naive graph community detection (Louvain, Connected Components) collapses distinct client clusters into massive false-positive mega-clusters when connected through high-degree hub nodes (e.g. public Wi-Fi, corporate CGNAT gateways, cloud proxy IPs).

## Options considered

- **Neo4j / Spanner Graph**: Managed graph cluster. Pros: handles billions of edges natively. Cons: substantial baseline infrastructure cost ($500+/mo), network boundary latency, authentication overhead, not scale-to-zero.
- **In-Memory NetworkX with Degree-Penalized Hub Suppression (Chosen)**: Graph stored in-memory, rehydrated from Parquet edge-lists on container warm-start. High-degree hubs (degree > 50) have edge weights penalized or isolated during community detection. Pros: sub-millisecond local graph traversal, zero external infrastructure cost, precise ring isolation without false mega-clusters.
- **GraphBLAS / cuGraph**: Specialized GPU/sparse matrix graph libraries. Cons: complex C/CUDA dependencies incompatible with lightweight Cloud Run CPU runners.

## Decision

Adopt **NetworkX with Hub Suppression and Parquet Snapshot Warm-Start** (`InMemoryGraphEngine`). High-degree infrastructural hubs are identified with an `is_shared_context` attribute and dynamically suppressed or penalized during ring extraction and community clustering. State is rehydrated on container boot from tiered Parquet snapshots.

## Consequences

- Positive: Microsecond graph traversals for AML Sentinel and Fraud Sentinel agents.
- Positive: Total elimination of false-positive ring mergers caused by shared CGNAT/office IPs.
- Negative: Single-container memory limit bounds graph scale to ~2M edges (adequate for active operational sliding window).
- Production evolution path: If operational sliding window exceeds 2M edges, Spanner Graph is documented as the scale-out target.

## Evidence

Spike S-05 benchmarks; test suite in `FEIOS/tests/ontology/test_graph_engine.py` demonstrating zero false mergers across synthetic CGNAT hubs.

## Revisit when

Operational active graph exceeds 2 million edges or cross-region distributed multi-master graph updates become mandatory.
