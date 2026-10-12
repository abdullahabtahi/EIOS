# Implementation Plan: Production-Grade Convergence & Sovereign Hardening

**Branch**: `019-production-grade-convergence` | **Date**: 2026-10-11 | **Spec**: [spec.md](./spec.md)

---

## Summary

This plan elevates the FEIOS platform from a sophisticated PoC into a full sovereign institutional-grade system. It addresses all gaps identified in the architectural comparison matrix:
1. **Zero Invariant Violations**: Resolve the 8 failing tests across ADR-002 vendor isolation, memory manager signatures, and schema copy paths.
2. **Live Frontend-Backend Wiring**: Expose FastAPI REST and SSE streaming endpoints (`fastapi.sse.EventSourceResponse`) connecting the live DuckDB Hot State store to the Next.js Cockpit.
3. **Hardware-Accelerated Relational Graph (WebGL / Canvas)**: Replace static 5-node SVG mockup with an interactive HTML5 Canvas / WebGL force-directed simulation capable of rendering 1,000+ nodes at 60 FPS with dynamic CGNAT proxy hub collapse ($k > 100$).
4. **External Cashier Webhook & Sentinel Interception**: Implement an authenticated webhook listener (`/api/v1/webhooks/cashier/withdrawal`) with HMAC SHA-256 verification and in-line `WithdrawalSentinel` evaluation.
5. **Google Cloud BigQuery & GCS WORM Sync (ADR-007 / ADR-017)**: Add upstream atomic sequence ordering and export sync streaming to BigQuery external tables and GCS retention-locked storage.
6. **Institutional Operator Ergonomics**: Implement keyboard-first alert triage (`j`/`k`, `x`, `e`, `f`), global omnibox search (`Cmd+K`), and URL forensic deep-link state serialization.
7. **Branch-per-Scenario Sandboxing & QuantumBlack Drift Surveillance**: Add copy-on-write ontology branching for SCM What-If simulations and continuous Population Stability Index (PSI) monitoring.

---

## Technical Context

- **Languages/Versions**: Python 3.14 (Backend/Engines) & TypeScript / React 19 / Next.js 15 (Cockpit Frontend)
- **Primary Dependencies**:
  - Backend: `fastapi`, `uvicorn`, `duckdb`, `networkx`, `google-cloud-bigquery`, `scipy`, `numpy`, `pandas`, `pydantic`
  - Frontend: `next`, `react`, `react-dom`, HTML5 Canvas / WebGL force layout, Tailwind CSS (Palantir Sovereign Light)
- **Storage**: In-memory DuckDB Hot State Engine + Append-only SQLite/DuckDB Action Outbox Ledger + BigQuery Lakehouse sync
- **Testing**: `pytest` (2,373 tests), Playwright / Next.js component testing
- **Performance Goals**:
  - Test Suite: 100.0% pass rate in $< 65\text{s}$
  - Graph Rendering: $\ge 55\text{ FPS}$ on 1,000 nodes / 2,500 edges
  - Webhook In-Line SLA: $< 150\text{ms}$ pre-settlement decision
  - UI What-If Shock Propagation: $< 50\text{ms}$ client / $< 100\text{ms}$ server round-trip

---

## Touched Files & Layout

```text
FEIOS/
├── src/eios/
│   ├── conversation/
│   │   ├── client.py               # [REPAIR] Decouple direct vendor SDK import behind gateway
│   │   └── memory.py               # [REPAIR] Fix keyword args and helper methods (merge_evidence)
│   ├── api/
│   │   ├── app.py                  # [NEW] FastAPI application exposing domain hot state & webhooks
│   │   ├── routes_churn.py         # [NEW] /api/v1/churn endpoints
│   │   ├── routes_fraud.py         # [NEW] /api/v1/fraud endpoints
│   │   ├── routes_aml.py           # [NEW] /api/v1/aml endpoints
│   │   ├── routes_synthesis.py     # [NEW] /api/v1/synthesis endpoints
│   │   └── routes_webhooks.py      # [NEW] /api/v1/webhooks/cashier/withdrawal in-line sentinel
│   ├── ontology/
│   │   ├── actions/
│   │   │   └── outbox_ledger.py    # [NEW/REPAIR] Persistent outbox with SHA-256 chaining & BigQuery sync
│   │   └── branching/
│   │       └── scenario_sandbox.py # [NEW] Branch-per-scenario copy-on-write ontology sandbox
│   └── monitoring/
│       └── drift_surveillance.py   # [NEW] QuantumBlack PSI & Brier calibration monitor
tests/
├── contract/test_schema_copies.py  # [REPAIR] Sync schema directory
└── test_conversation_memory.py     # [VERIFY] Confirm 4 passing memory tests
web-prototype/src/
├── components/cockpit/
│   ├── common/
│   │   └── topological-graph.tsx   # [REWRITE] Upgrade from static SVG to dynamic HTML5 Canvas / WebGL
│   ├── shell/
│   │   ├── copilot-command-bar.tsx # [ENHANCE] Wire Cmd+K omnibox & keyboard shortcuts
│   │   └── triage-rail.tsx         # [ENHANCE] Keyboard j/k navigation and action hotkeys
│   ├── state/
│   │   ├── cockpit-context.tsx     # [ENHANCE] URL search param state sync
│   │   └── api-bridge.ts           # [NEW] Live FastAPI client with SSE streaming & replay fallback
│   └── workstations/
│       ├── partner-workstation.tsx # [ENHANCE] Live data binding
│       └── aml-workstation.tsx     # [ENHANCE] Live data binding
```
