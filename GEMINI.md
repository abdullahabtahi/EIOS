# GEMINI.md

Guidance and behavioral constraints for Google Antigravity and Gemini Code Assist in the **Enterprise Intelligence Operating System (EIOS)** repository.

## 1. Orientation & Role

- **System**: Enterprise Intelligence Operating System (EIOS) — an autonomous, regulator-grade decision-intelligence platform (client persona: Deriv).
- **Production Root**: `EIOS/` (Python 3.14 backend managed with `uv`, Next.js 15 cockpit in `EIOS/web-prototype/`).
- **Role**: Forward Deployed Engineer (FDE) pair-programmer. Plan concisely, build 80/20, evaluate continuously, and never break existing contracts.

### Key Documentation Links
- Agent Architecture & Topology: `docs/agent-architecture.md`
- Data Strategy & Warm Tier: `docs/data-strategy.md`, `docs/warm-tier.md`
- Geospatial Product Direction: `docs/financial_geospatial.md`
- Deployment & Environments: `docs/runbooks/cockpit-deploy.md`, `EIOS/docs/environments.md`
- ADR Index: `docs/spikes_and_adrs.md`

## 2. Constitutional Invariants (Non-Negotiable)

1. **RL-1 (No LLM-Computed Metrics)**: Every number originates from a deterministic engine (DuckDB, BigQuery, Flink). The LLM explains and synthesizes, never computes arithmetic.
2. **RL-2 (No Autonomous Write-Back)**: Agents propose only. Any state change requires an expiring, Cloud KMS-signed Action Intent approved by an operator under four-eyes governance.
3. **RL-3 (Honest Uncertainty)**: Causal claims must pass the placebo refuter (p > 0.05, confidence >= 0.80); otherwise marked "Correlation Only".
4. **RL-4 (CGNAT Hub Suppression)**: Shared-IP nodes with degree > 100 are pruned from laundering rings.
5. **RL-5 (WORM Decision Ledger)**: Monotonic sequence numbers and SHA-256 chaining on all approvals.
6. **RL-6 (What-If Speed & Attribution)**: Shocks propagate in < 200 ms with attribution summing exactly to 100.0%.
7. **RL-7 (Deterministic Replay)**: Outages serve labelled verified replay, never invented state. Copilot outage fails closed with HTTP 503.

## 3. Essential Commands

### Backend (`EIOS/`)
- Setup: `make setup`
- Test suite: `make test` or `uv run pytest tests/cockpit/test_server_gateway.py -q`
- Lint & Types: `make lint` and `make types` (strict mypy)
- Full PR gate validation: `uv run python -m tools.gates.run_gate check`
- **Gateway Server**:
  ```bash
  PYTHONPATH=src uv run uvicorn eios.api.app:app --host 127.0.0.1 --port 8002
  ```
  *(Always run `eios.api.app:app`. Do not run `eios.cockpit.server:app` directly, as domain routers like AML, Churn, and Geo will 404).*

### Frontend (`EIOS/web-prototype/`)
- Dev server: `npm run dev -- -p 3000` (runs with `--webpack`)
- Production build & test: `npm run build && npm run start -- -p 3012`
- Type checking: `npx tsc --noEmit` (must yield 0 errors)
- Unit tests: `npm test` or `npx vitest run <file>`
- Linter: `npm run lint`

## 4. Multi-Agent & Environment Gotchas

- **Ports & CORS**:
  - Default ports: Web `3000`, Backend `8002` (port `8000` is legacy).
  - Alternative local port: Web `3012`. `src/eios/cockpit/auth.py` allows `http://localhost:3012` in `DEV_CORS_ORIGINS`.
  - When switching ports or running across containers, ensure `EIOS_CORS_ORIGINS` includes the active origins and `EIOS_BACKEND_URL=http://127.0.0.1:8002` is supplied to Next.js.
- **Cockpit Graph Selection Contract**:
  - In `TopologicalGraphCanvas`, clicking peripheral counterparties (mule accounts, payment agents, device tokens) must **only** update local inspector selection (`setSelectedNode`).
  - **Never** invoke `selectEntity(node.id)` on peripheral nodes. Doing so mutates `activeEntityId`, triggering unnecessary dossier reloads (404 on non-case IDs) and resetting the inspector.
  - `focalId` must remain anchored to the case seed dossier (`activeTriageItemId` / `CR84920`) so force-directed simulation does not pull counterparties to `(0, 0)` or cause physics jitter.
- **Core Web Vitals & Benchmarks**:
  - Evaluate CWV (CLS < 0.05, LCP < 1.2s, JS Heap ~7 MB) strictly against the **production bundle** (`npm run build && npm run start`).
  - Dev mode (`npm run dev`) includes on-the-fly TypeScript compilation, react source maps, and HMR overhead (~120 MB heap, 2.8s render delay), which is normal for development and not a performance regression.
- **Google Cloud Settings**:
  - Active dev project: `eios-hackathon`. Legacy default is `spatial-cat-489006-a4`—always explicitly supply `--project eios-hackathon` and set `GOOGLE_CLOUD_QUOTA_PROJECT=eios-hackathon`.

## 5. Architecture & Contracts

- **L0 `foundry/`**: Synthetic seeded generators. Evaluated by benchmarks; engines never read truth tables directly.
- **L1 `ingestion/` & `contracts/`**: Pub/Sub ingestion, schema validation (breaches to DLQ, never dropped), DuckDB hot state.
- **L2 `ontology/`**: Metrics registry (ADR-003), graph engine (ADR-004), Action Intents (`intent_hub.py`, Cloud KMS signer).
- **L3 `assistant/`**: ADK assistant runtime (ADR-019). No client-side fallback; plain figures must be cited from tool outputs; outages fail closed (HTTP 503).
- **L4 `cockpit/`**: FastAPI gateway (`server.py`), `auth.py` Firebase verification, Next.js workstation dashboards.

## 6. Development & PR Safety Rules

- **Strict Approval Policy**:
  - **NO MERGING without explicit user approval.** Never merge a pull request autonomously.
  - **NO DEPLOYING without explicit user approval.** Cloud Run and Terraform applies require operator sign-off.
- **Clean Commits & Trunk-Based Branches**:
  - Conventional commits (`feat:`, `fix:`, `docs:`, `perf:`).
  - No `Co-Authored-By` trailers.
  - Never run `git add -A` over infra or build outputs (e.g. Terraform plans or `.next` artifacts).
  - Verify all gates (`make check`, `npx tsc --noEmit`) pass cleanly before pushing.
