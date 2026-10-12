# ADR-004: Graph engine for ring detection
Status: Accepted
Date: 2026-03-14
Context: Ring detection needs community search over a graph of up to 1M edges.
Hub nodes (shared IPs) cause false merges.
Options considered: A) NetworkX with hub suppression. B) Managed graph database.
Decision: Use NetworkX with hub suppression for the POC.
Consequences: Positive: no new service. Negative: memory ceiling.
Evidence: S-05, benchmark report in evals/graph.
Revisit when: graph exceeds the measured ceiling.
