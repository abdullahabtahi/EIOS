# CLAUDE.md

This file provides critical guidance and navigation instructions for Claude Code (and other autonomous AI agents) working within this repository.

---

## 1. Repository Orientation

Forward Deployed Engineering (FDE) engagement, POC → Production, for the **Enterprise Intelligence Operating System (EIOS)**. `EIOS/` is the primary self-contained production root (Python backend via `uv`, Next.js cockpit in `EIOS/web-prototype/`). Requirement sources live in `docs/` (canonical briefs in `docs/brief/`); feature specs live in `specs/`. UI design rules and the persona/workstation matrix are in `EIOS/web-prototype/CLAUDE.md`.

---

## 2. Non-Obvious Commands

- **Network-enabled tests**: `EIOS_TEST_NETWORK=1 uv run pytest -q` (default test runs are offline)
- **All 13 PR gates**: `make check` (run from `EIOS/`)
- **Web typecheck**: `npx tsc --noEmit` must be 0 errors (run from `EIOS/web-prototype/`)

---

## 5. Constitutional Invariants (Non-Negotiable)

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

## 6. Provenance & Labelling Regime

Every quantitative figure or claim in the codebase, tests, fixtures, and UI must carry an explicit provenance label:
- `[BRIEF]`: Cited directly from canonical business requirements (`docs/brief/*`).
- `[ASSUMPTION]`: Explicit operational assumption documented in architecture plan.
- `[ILLUSTRATIVE]`: UI walkthrough or mockup placeholder clearly labeled as non-production fixture.
- `[TARGET]`: Formal SLO or performance commitment.
- `[SPIKE]`: Temporary exploratory metric pending Architectural Decision Record (ADR).

---

## 7. Spec-Driven Workflow (Spec-Kit)

When developing or modifying features, follow the established spec pipeline in `specs/`:
```
Constitution → Specify → Clarify → Plan → Tasks → Analyze → Implement
```
- Available skills: `speckit-specify`, `speckit-clarify`, `speckit-plan`, `speckit-tasks`, `speckit-analyze`, `speckit-implement`, `speckit-converge`.
- Always inspect existing `spec.md`, `plan.md`, and `tasks.md` in `specs/<feature-dir>/` before introducing new domain models or endpoints.
