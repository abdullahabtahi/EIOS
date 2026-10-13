# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 1. Repository Orientation

Forward Deployed Engineering (FDE) engagement, POC → Production, for the **Enterprise Intelligence Operating System (EIOS)**. `EIOS/` is the primary self-contained production root (Python backend via `uv`, Next.js cockpit in `EIOS/web-prototype/`). Requirement sources live in `docs/` (canonical briefs in `docs/brief/`); feature specs live in `specs/`. UI design rules and the persona/workstation matrix are in `EIOS/web-prototype/CLAUDE.md`.

---

## 2. Commands

Backend (run from `EIOS/`, Python 3.14 via `uv`):
- `make setup` (uv sync), `make test` (pytest `-n auto`), `make lint` (ruff check + format check), `make types` (strict mypy)
- **Single test**: `uv run pytest tests/cockpit/test_server_gateway.py::test_name -q`
- **Network-enabled tests**: `EIOS_TEST_NETWORK=1 uv run pytest -q` (default runs are offline; markers `requires_network`, `requires_emulator`, `requires_cloud`)
- **All 13 PR gates**: `make check`. Same gates and same `config/gates.yaml` as `.github/workflows/pr.yml`; reports land in `evals/reports/`.
- Cockpit gateway: `uv run uvicorn eios.cockpit.server:app --port 8002` (the port `api-bridge.ts` falls back to on localhost)

Web (run from `EIOS/web-prototype/`): `npm run dev` / `build` (both `--webpack`), `npm run lint`, `npm test` (vitest; single file: `npx vitest run <path>`), `npx tsc --noEmit` must be 0 errors.

---

## 3. Architecture (big picture)

Layered, each layer consuming the one below only through contracts:
- **L0 `foundry/`**: seeded synthetic generators (hard negatives, sealed holdout, placebo edges). All current data is synthetic.
- **L1 `ingestion/`, `contracts/`**: Pub/Sub, then Pydantic contract validation (breach goes to DLQ, never silent drop), then DuckDB hot state with Parquet warm start.
- **L2 `ontology/`**: objects/links/actions/security markings. `metrics/` is the DuckDB semantic registry (ADR-003), `graph/` is NetworkX with CGNAT hub suppression (ADR-004), `omcp/` is the tool server agents must use, and `actions/` holds Action Intents (KMS `signer.py`, `sequencer.py`, `worm.py` ledger, `sink.py` simulated write-back). `auditor/` is the Metric Auditor Gate.
- **L3 `conversation/`**: LangGraph supervisor and specialists (ADR-016 blackboard, at most 3 reflection cycles). Specialists reach data only through OMCP tools, and the egress node scans every response with the Auditor Gate. Models are called only via `llm_gateway/` (prompt-locked, replay cache, per-env config in `config/llm_gateway.*.yaml`).
- **Domain modules** (`aml/`, `churn/`, `fraud/`, `synthesis/` with SCM, forecast and AIPW) produce the deterministic numbers that L3 narrates.
- **L4 `cockpit/`**: `server.py` is the FastAPI gateway for the Next.js cockpit (workstation state, simulate, stage/authorize action, copilot query, flywheel feedback, audit verify). `eios.api.app` is a separate FastAPI app for domain routes. The web `api-bridge.ts` serves deterministic fixtures when the backend is unreachable, so a working UI does not prove the backend wiring.

Process gates: new gates are rows in `config/gates.yaml` (never runner edits). Quarantined gates in `config/quarantine.yaml` fail the run after their `expires` date. The lint gate also runs `tools.repo_checks` (file size, forbidden literals, frozen models, pinned dependencies). `adr_check` requires ADRs in `docs/evidence/adrs/` to agree with the index in `docs/spikes_and_adrs.md`.

---

## 4. Constitutional Invariants (Non-Negotiable)

1. **LLMs Never Compute Business Metrics (Principle I / RL-1)**:
   - All numbers must originate from deterministic analytical engines (DuckDB Semantic Engine, BigQuery metrics job, or Flink streaming).
   - The LLM's role is synthesis, explanation, and draft narrative generation only.
2. **No Autonomous Write-Back (Principle II / RL-2)**:
   - Agents can only propose actions.
   - Every state mutation requires a Cloud KMS-signed (ECDSA P-256), expiring Action Intent approved by a human operator under Four-Eyes dual control.
3. **Honest Uncertainty & Causal Evidence Gate (Principle III / RL-3)**:
   - Causal vectors are displayed as verified causal only if placebo-treatment refuter $p > 0.05$ and confidence $\ge 0.80$. Otherwise, explicitly rendered as "Correlation Only".
4. **CGNAT False Positive Hub Suppression (Feature 010 / RL-4)**:
   - Shared IP gateway nodes with degree $k > 100$ are automatically collapsed and suppressed from false-positive money laundering rings.
5. **Immutable WORM Decision Ledger (Feature 011 / RL-5)**:
   - Monotonic sequence numbers with SHA-256 cryptographic chaining lock every approval action.
6. **Sub-200ms Parametric Propagation & 100% Attribution (Feature 002 / RL-6)**:
   - What-If shocks propagate in $< 200\text{ms}$ with verified $\sum \text{Attribution} = 100.0\%$.
7. **Deterministic Offline Replay Fallback (Principle VIII / RL-7)**:
   - Network partition or presentation outage triggers verified cryptographic cache replay, never hallucinated states.

---

## 5. Provenance & Labelling Regime

Every quantitative figure or claim in the codebase, tests, fixtures, and UI must carry an explicit provenance label:
- `[BRIEF]`: Cited directly from canonical business requirements (`docs/brief/*`).
- `[ASSUMPTION]`: Explicit operational assumption documented in architecture plan.
- `[ILLUSTRATIVE]`: UI walkthrough or mockup placeholder clearly labeled as non-production fixture.
- `[TARGET]`: Formal SLO or performance commitment.
- `[SPIKE]`: Temporary exploratory metric pending Architectural Decision Record (ADR).

---

## 6. Spec-Driven Workflow (Spec-Kit)

When developing or modifying features, follow the established spec pipeline in `specs/`:
```
Constitution → Specify → Clarify → Plan → Tasks → Analyze → Implement
```
- Available skills: `speckit-specify`, `speckit-clarify`, `speckit-plan`, `speckit-tasks`, `speckit-analyze`, `speckit-implement`, `speckit-converge`.
- Always inspect existing `spec.md`, `plan.md`, and `tasks.md` in `specs/<feature-dir>/` before introducing new domain models or endpoints.
