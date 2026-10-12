# S-05: Graph scale ceiling for NetworkX plus Louvain
Id: S-05
Question: Where is the memory and time ceiling of the in-memory graph engine?
Time box: 1 day [TARGET]
Owner: platform-team
Outcome: Ceiling measured at the stated edge count.
Linked ADR: ADR-004
State: closed
Method: Generate graphs from 10k to 1M edges and time build and community search.
Data: Synthetic graphs, seed 7.
Result: Build time grows linearly; hub suppression removes shared-IP merges.
Decision: Keep NetworkX for the POC.
Date: 2026-03-10
