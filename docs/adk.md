# EIOS Conversational Agent: LangGraph to Google ADK

**Status**: the ADK assistant is the only copilot runtime; the legacy copilot and the LangGraph mesh are deleted (ADR-019 Accepted). **Updated**: 2026-10-14. **Owner**: you. **Companions**: `adk-research.md` (research, pre-mortem, spec plan), `data-strategy.md`, `financial_geospatial.md` (v3, section 7.2 item 1), `EIOS/docs/adr/016-*` (superseded by ADR-019), `specs/018-genai-conversational-agent`.
**Tags**: `[ASSUMPTION]` `[TARGET]` `[SPIKE]`. "Verified" means checked on 2026-10-13.

> Principle: build less custom code. Replace what ADK, MCP Toolbox, Agent Search and Model Armor already do; keep only what is our IP (intent hub, KMS signing, WORM ledger, metric semantics, domain engines, red-line tests).

---

## 1. Status board

| # | Phase | Status | Exit criterion |
|---|---|---|---|
| A0 | Dependency alignment PR: `google-adk[gcp]==2.11.0`, `fastapi>=0.133,<0.142.2`, `opentelemetry-*<=1.42.1` (`fastapi>=0.142.2` itself needs `opentelemetry>=1.44`, so both move together) | A-9 approved 2026-10-14; PR `chore/adk-dependency-pins` with Dependabot ignores tied to ADK's cap: full suite identical on old and new pins, 0 advisories (`adk-research.md` section 3.2) | `make check` green on the new pins |
| A1 | ADR superseding 016, and spec 021 | Done: ADR-019 Accepted, ADR-016 Superseded by ADR-019, spec 021 merged | Reviewed; `open_decisions.yaml` updated |
| A2 | Eval set first (probe cases below plus golden questions for expected tool calls) | Done (spec 022): 22 golden cases `[MEASURED]`, 15 attacks `[MEASURED]`, deterministic judges and a port any runtime plugs into. Baseline in `agent-baseline.md`: 28 of 61 case results fail `[MEASURED]` against today's engine | Suite runs red against today's engine, as expected: met |
| A3 | Thin slice: one ADK agent per workstation over the governed tool port, reference-based answers | Done (specs 021 and 023): the ADK assistant serves the cockpit and the legacy copilot is deleted. Live quality is in `agent-baseline.md` section 7. On a model outage the endpoint answers 503 `offline`; there is no replay (decision of 2026-10-14) | Gates in `evals/agent/thresholds.yaml`; the three-repeat gating run is still owed |
| A4 | Sub-agents, Agent Search RAG, Model Armor plugin, ADK session service on Firestore | Session service and the Model Armor plugin are built in code; the Model Armor templates need Terraform (ask first); RAG is spec 024 | Templates exist; RAG answers carry citations |
| A5 | Wire the browser action shelf to real stage/authorize; remove client-side fabricated copilot fallbacks | Done for the copilot (stage and authorize hit the intent hub; the chat lives in the dossier column). The workstation fallbacks in `api-bridge.ts` remain | Shelf actions hit the intent hub |

Sequencing (revised 2026-10-13): A0-A3 do not wait on the wider data work. They need only the DDD context map (`data-strategy.md` D0) and a tool port, and they run on the existing hot state. Real tables behind MCP Toolbox come with the warm tier (`data-strategy.md` D4). Note `data-strategy.md` R1: the deployed API has no loaded hot state, so tools backed by it need a data path in the deployed environment, or must label themselves fixture, before A3 can claim live answers. Fix R2 (vault salt) before any tool exposes pseudonymised data.

## 2. Defect register (the legacy copilot, deleted 2026-10-14)

Kept as history: the code these rows name no longer exists, so the file links were removed.

| ID | Defect | Where | Fixed by |
|---|---|---|---|
| B1 | All operators share session `sess_default`; memory leaks across users | [server.py](../EIOS/src/eios/cockpit/server.py) | Fixed at the endpoint by spec 023 (session per verified operator and workstation) |
| B2 | Browser sends `activeEntityId`, server expects `context_entity_id`; no session id sent. Server now accepts both names (spec 023); the browser rename and the entity reaching the engine ride with spec 021 and 030 | `copilot-command-bar.tsx` | A3 |
| B3 | Role is taken from the request body, not the verified operator. The role match also never succeeded, so every query ran as executive | [server.py](../EIOS/src/eios/cockpit/server.py) | Fixed by spec 023: the verified operator is the identity, an unknown workstation is refused (422), the workstation only scopes the tools |
| B4 | No multi-turn memory on the live path; raw query sent, resolved query unused | `copilot_engine.py` | A3 |
| B5 | Replay path is hardcoded keyword branches with fixed entity ids | same | A3 |
| B6 | Keyword routing, keyword adversarial blocklist, `"sec"` policy trigger | same, `rag_tools.py` | A3-A4 (Model Armor) |
| B7 | Tools are fixtures; copilot bypasses the governed OMCP server and markings | `tools.py` | A3 |
| B8 | Citations carry tool name, not metric id; label used as value | copilot_engine | A3 |
| B9 | `ThreadCheckpointer` is SQLite `:memory:`: lost on restart, not shared | `checkpointer.py` | A4 |
| B10 | Turns up to 50-65 s (manual loop plus correction rounds) `[SPIKE]` from CLAUDE.md | copilot_engine | A3 (reference check removes most retries) |
| B11 | `ActionIntentToken` defaults to a simulated signature and a legacy-project KMS key | `models.py` | A3 (remove defaults; signing only via the intent hub) |
| B12 | LangGraph path is a stub (constant strings, unset `compliance_hold`) | `graph.py`, `supervisor.py` | A4 (delete) |

## 3. The auditor: why it is replaced

Measured on 2026-10-13 against the repo's own fixture tool results (script run in the session scratchpad, not committed yet):

| Answer | Should be | Result |
|---|---|---|
| Risk score of CR84920 is 16 (16 is the discrepancy multiplier) | block | passed |
| Net revenue is $38,200 (real $3,820,000) | block | passed |
| Velocity is 1600 transfers (real 16) | block | passed |
| "about three million dollars", "sixteen accounts" | block | passed |
| Income was $500 per week (figure is monthly) | block | passed |
| Revenue is about $3.8 million (true) | pass | blocked |
| 3 key findings across 2 sources | pass | blocked |

Cause: it checks "does this digit string appear anywhere in tool output", with a x100 scale tolerance and many regex exemptions. There is no binding between a claim and its source field.

**Replacement design**: the model never writes figures. It writes references (`{{fact:<call_id>.<field>}}`); a deterministic renderer fills value, unit and as-of from the tool result; any free-text numeral left over must be a short exempt category. Run it as an ADK plugin so every agent is covered. Add Model Armor (injection, PII) at the edges, optionally the Check Grounding API for prose claims (untested on numbers), and ADK eval for regression. The seven rows above become permanent tests.

## 4. Target architecture

| Today | Becomes |
|---|---|
| Manual tool loop, SDK function calling disabled | ADK `LlmAgent` with function tools (re-test automatic calling on Python 3.14) |
| Regex auditor plus correction loop | Reference renderer plus residue check as an ADK plugin |
| Keyword adversarial list | Model Armor plugin |
| `tools.py` fixtures | MCP Toolbox named tools over BigQuery; domain engines as function tools |
| Fake `query_policy_search` | Vertex AI Search / Agent Search with passage citations (check whether its tool can share an agent with function tools; otherwise use a sub-agent) |
| `ThreadCheckpointer`, pronoun resolver | ADK session service on Firestore; entity anchors in session state |
| `stage_action_intent` | ADK tool confirmation; intent hub stays the only signer |
| Keyword routers, LangGraph supervisor | ADK sub-agents with descriptions; deterministic routing for compliance hold |
| Replay | Labelled replay via callback or workflow route: `is_replay_fallback` and `fallback_reason` always set |

Kept as-is: constitutional invariants RL-1..RL-7, the allow-listed tool set, the 3-cycle bound, compliance-hold arbitration, KMS-signed human-in-the-loop.
Database access: never expose generic `execute_sql` to the model; only named parameterised tools.

## 5. Risks and unverified items

| Item | State |
|---|---|
| `google-adk` 2.11.0 resolves on Python 3.14 with `opentelemetry-*` 1.42.1, `fastapi` 0.141.1, `websockets` 15.0.1; cause is a chain (ADK caps OpenTelemetry at 1.42.1, `fastapi>=0.142.2` needs 1.44 or newer) | Verified, full suite run on the new pins; handled by A0 |
| Vendor SDK rule (ADR-002): `google.adk` and `mcp` imports need an allowed path | Open; resolve in the A1 ADR |
| ADK tool loop on Python 3.14 (CLAUDE.md records an automatic-function-calling failure with raw google-genai) | Tool loop, plugins and first-party integrations verified with a scripted model (`adk-research.md` S-ADK-1); live Gemini unverified (S-ADK-2) |
| MCP Toolbox ADK SDK on Python 3.14; Toolbox as a new private Cloud Run service (identity, `infra/identities.yaml`) | Unverified |
| Offline tests need a Toolbox stand-in (SQLite or stub) | Open |
| Google docs search tool (Developer Knowledge MCP) rejected its API key this session; Check Grounding and Model Armor details come from public doc pages | Known limitation |
| The legacy conversation tests asserted the old copilot | Retired with the code; what they said about OMCP and endpoint identity is kept (ADR-019 Evidence) |

## 6. Open decisions

| ID | Decision | Recommendation | Status |
|---|---|---|---|
| A-1 | Proceed with ADR (supersede 016) and spec 021 as drafts | Yes | Open |
| A-2 | Governed read store behind Toolbox: BigQuery or DuckDB with a small MCP server | BigQuery (same as D-2 in `data-strategy.md`) | Open |
| A-3 | Keep OMCP as the single policy and markings façade, or collapse it into Toolbox plus ADK tools | Keep the façade, implemented on the official MCP SDK; open to your call | Open |
| A-4 | Order: D0 and D1 of `data-strategy.md` first (context map, defects R1-R4), then A0-A3 in parallel with D2-D6 | Yes (revised: no longer wait for the full data slice) | Open |
| A-5 | Pin `google-adk` to 2.11.0 and review monthly | Yes | Open |
