# Spikes and decisions

## 1. Spikes

| ID | Question | Why unverified | Method | Decision it unlocks | Fallback |
|---|---|---|---|---|---|
| [**S-01**](adr/S-01-llm-availability-and-pricing.md) | Which models are available? | Not yet checked | Query provider docs | ADR-050 | Hypothetical decision recorded without a file | Accepted | None | — |
| ADR-002 | Provider-agnostic gateway |

## 2. ADR index

| ADR | Decision | Status | Default / current lean | Depends on |
|---|---|---|---|---|
| [ADR-001](adr/001-ontology-as-data-logic-action-security.md) | Ontology as data + logic + action + security (not just a semantic layer) | Accepted | Four-fold | — |
| ADR-050 | Hypothetical decision recorded without a file | Accepted | None | — |
| ADR-002 | LLM gateway abstraction & model selection | Open | Provider-agnostic gateway | S-01 |
