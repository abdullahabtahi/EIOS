# Spikes and ADRs (fixture)

## 1. Spikes

| ID | Question | Why unverified | Method | Decision it unlocks | Fallback |
|---|---|---|---|---|---|
| **S-01** | Where is the graph ceiling? | Not measured | Time graph builds | ADR-003 | Snapshot |
| **S-02** | Which model is available? | Not checked | Query docs | ADR-002 | Gateway |

## 2. ADR index

| ADR | Decision | Status | Default / current lean | Depends on |
|---|---|---|---|---|
| ADR-001 | Ontology as data and logic | Accepted | Four-fold | — |
| ADR-002 | LLM gateway abstraction | Open | Provider-agnostic | S-02 |
| ADR-003 | Graph engine choice | Proposed | NetworkX | S-01 |
| ADR-004 | Approval hosting v1 | Superseded by ADR-005 | — | — |
| ADR-005 | Approval hosting v2 | Accepted | — | — |
| ADR-006 | Ledger anchors | Proposed | — | — |
