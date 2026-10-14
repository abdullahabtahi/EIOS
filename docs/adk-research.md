# ADK Stage: Research, Validation, Pre-mortem and Spec Plan

**Status**: DRAFT for your review, nothing built. **Updated**: 2026-10-13. **Companions**: `adk.md` (status board and defects), `data-strategy.md`, `lighthouse.md` (metrics M1-M6), ADR-018 (Proposed).
**Evidence tiers** (used on every finding): **RUN** = executed by me in a scratch spike; **SRC** = read in the installed `google-adk` 2.11.0 package source; **DOC** = read on a public Google or ADK documentation page; **INF** = my inference from the above; **UNV** = not verified (third-party or not tested). Dates are 2026-10-13 unless stated.

> Purpose: decide what to build, in what order, and what would make it fail, before writing any spec. The deliverable of this stage is a better lighthouse metric, not a framework swap.

---

## 1. Verdict

1. **Worth doing, for a narrower reason than "migrate to ADK".** A generic chat over BigQuery is a commodity (Google ships it). What we can defend is: numbers you can audit, actions you can govern, evidence you can replay. ADK is the runtime that lets us delete custom code (tool loop, session store, guardrail plumbing, eval harness, telemetry) so the effort goes into those three things.
2. **ADK 2.11.0 is viable on our stack.** A scripted tool loop with plugin hooks ran on Python 3.14.4 (RUN, S-ADK-1). The first-party Firestore session service, Model Armor plugin, Agent Search tool, BigQuery toolset and graph `Workflow` all import there (RUN). It is not yet tested against live Gemini (S-ADK-2).
3. **Three things in the earlier plan change** (section 3): dependency pins are a two-package conflict, not one; ADK ships far more first-party Google integration than assumed (so less custom code); and its Model Armor plugin does not screen tool results, which is the exact path partner-comms injection would take.
4. **Build order changes.** Quality gates first (red against today's copilot), then the typed tool port, then the ADK runtime, then knowledge retrieval, then the deployed event-driven data path, then geo (section 6).
5. **Where an LLM belongs.** Evidence assembly, narrative, SAR drafting, tool selection, explanation. Where it does not: detection, scoring, any figure (RL-1). The agent is a thin governed interface over deterministic engines.

## 2. Value validation by workstation

| Workstation | Real problem (`[BRIEF]`) | What the agent does | What it must never do | Measured by |
|---|---|---|---|---|
| AML investigator | About 2,000 alerts a week, about 95% false positives, context from 5+ systems, SAR deadlines (`monitoring.md`) | Assemble a cited dossier, answer follow-ups, draft the SAR, propose a hold | Score, file, approve, or state a figure not from a tool | M1, M2, M3, M4, M6 |
| Partner manager | Thousands of partners, silent disengagement, commission disputes nobody connects (`churn.md`); coordinated opposite trading and referral rings (`fraud.md`) | Rank this week's partners with drivers, connect tickets to commission trends, draft outreach, propose a review | Accuse a partner (claims limited to observed facts), act on text found inside partner comms | M3, M4, M5 |
| Executive | Cross-domain "why is LTV declining in APAC" takes days (`data.md`) | Synthesise across domains from governed metrics and the causal gate; run what-if through the scenario engine | Present correlation as cause (RL-3), invent a driver | M3, M5 |
| Compliance auditor | Prove the decision trail | Explain ledger state; the checks stay deterministic | Anything beyond read and explain | RL-5 tests |
| Data operations | Pipeline and DLQ health | Explain incidents from the DQ board | Re-drive or mutate | RL tests |
| Financial geospatial (cross-cutting) | Where is this ring's money going; which regional cohorts decay together | Choose and combine spatial tools; emit map commands; narrate | Street-level or natural-person geocoding | New metric, set in spec 026 |

Honest read: the strongest case is AML (clear brief, measurable time, regulator-shaped output) and the partner worklist. The executive chat is the least differentiated and the riskiest; it earns its place only through the causal gate and the scenario engine. Nothing here is measured: M1, M2, M5 still lack a timed baseline (`lighthouse.md`).

## 3. Research findings

### 3.1 What ADK 2.11.0 gives us, verified

| Finding | Tier | Consequence |
|---|---|---|
| Tool loop, `before/after_tool`, `after_model` hooks work on Python 3.14.4 with a scripted model | RUN | CLAUDE.md's "automatic function calling fails on 3.14" was about raw google-genai; ADK runs tools itself. Live-Gemini confirmation still needed (S-ADK-2) |
| `integrations/firestore`: `FirestoreSessionService` (takes a `firestore.AsyncClient`, so our named database works; stale-session detection) and a memory service | SRC, import RUN | Replaces `ThreadCheckpointer` with no custom store. Needs `google-cloud-firestore` (already a dependency) |
| `integrations/model_armor`: `ModelArmorPlugin`, ADK 2.8+, screens user input and model output, skips tool results, `block_on_screening_failure=True` by default, sets `model_armor_blocked` on the event | DOC, import RUN | Replaces the keyword adversarial list. **Gap: tool results are not screened** |
| `plugins/bigquery_agent_analytics_plugin`: logs agent events (LLM requests, tool calls) to BigQuery via the Write API; has event allow/deny lists, a `content_formatter` redaction boundary, 500 KB default content cap, GCS offload | SRC | Gives lighthouse section 8 instrumentation with no custom code. **Logs content by default, so redaction is a requirement** |
| `integrations/bigquery`: `BigQueryToolset` with `maximum_bytes_billed`, `max_query_result_rows` (default 50), `write_mode` (default BLOCKED), job labels, project guardrails. Includes `execute_sql`, `forecast`, `detect_anomalies`, `analyze_contribution`, `ask_data_insights`, `search_catalog` | SRC | Good guardrails, but `execute_sql` and `ask_data_insights` are free SQL for the model. Violates our rule unless filtered with `tool_filter` |
| `tools/discovery_engine_search_tool.py`: `DiscoveryEngineSearchTool` is a `FunctionTool` (Agent Search) | SRC | Can share an agent with other function tools. The built-in `VertexAiSearchTool` also can on v1.16+ via `bypass_multi_tools_limit=True` (DOC) |
| `tools/set_model_response_tool.py`: structured `output_schema` together with tools | SRC | A typed answer envelope (text with references, proposed actions, map commands) is possible without a formatter agent |
| Graph `Workflow` (2.0): function nodes, agent nodes, routes via `Event(route=...)`, `RequestInput` for human input | DOC, SRC, import RUN | Deterministic control flow for compliance hold and action staging without prompts. Young API; surfaces `[EXPERIMENTAL]` warnings |
| `adk eval` with `tool_trajectory_avg_score`, rubric and hallucination metrics, user simulation, and **custom metrics by Python import path** | DOC, SRC | Our deterministic faithfulness check becomes a first-class ADK metric and a CI gate |
| `integrations/agent_registry`, `agent_identity`, `eventarc`, `tools/pubsub`, `tools/spanner`, `toolbox_toolset`, `google_maps_grounding_tool` | SRC | Registry and gateway governance, event-driven triggers and Pub/Sub tools exist first-party |
| `to_a2a()` exposes an agent over A2A; Gemini Enterprise registers ADK agents hosted on Agent Runtime (GA 2026-04-20) and A2A agents (GA 2026-08-17); registration consumes a per-license daily creation quota; Model Armor is not applied automatically | DOC, search snippets for the dates (UNV on exact dates) | A channel, not a core dependency (decision A-3) |

### 3.2 Corrections to earlier plan documents

| Earlier claim (`adk.md` section 5) | Correction |
|---|---|
| "ADK downgrades `opentelemetry-*`, `fastapi`, `websockets`" listed as three equal items | One chain: ADK caps `opentelemetry-api/sdk` at 1.42.1 (SRC); our `fastapi>=0.142.2` itself requires `opentelemetry-api>=1.44` (RUN, uv resolver output); so **both** bounds must move. Resolved set in a scratch worktree: `google-adk[gcp]==2.11.0`, `fastapi 0.141.1`, `opentelemetry 1.42.1`, `websockets 15.0.1`, `google-genai 2.29.0`, LangGraph still resolves (RUN). **Full suite on the new pins: 2,592 passed, 6 failed, 3 collection errors, 7 expected failures.** All reproduce on the old pins in a fresh checkout (three coverage-fixture tests, three `tests/evals` collection errors) or are known timing tests that pass in isolation on both sets (`test_dq_monitor`, ontology benchmark) or the known quarantine test; so no regression is attributable to the pins. Closed 2026-10-14 on main (`66d5336`): the full parallel suite on the old pins gives 3,027 passed, 1 failed (`test_quarantine`), 7 expected failures `[MEASURED]`; the new pins give the identical result, and `vuln_scan` plus `pip-audit` over 173 locked packages report 0 advisories `[MEASURED]`. FastAPI 0.142.0 to 0.142.2 release notes hold no security fix (native OpenTelemetry, then two bug fixes). The A0 branch stays local until you approve A-9 |
| "ADK on Python 3.14 unverified" | Tool loop and imports verified (RUN); live Gemini and parallel tool calls remain open |
| "Fake `query_policy_search` becomes Agent Search" | Confirmed feasible as a function tool; corpus and licensing still to define (D-3) |
| OMCP is "the governed tool server" | OMCP dispatches by name (`_handle_<tool>`, no schemas, a number of duplicate handlers such as `get_client_aml_dossier` and `get_aml_entity_dossier`). ADK, MCP and Toolbox all need typed contracts, so ADR-018's tool contract is on the critical path (SRC of our own `server.py`) |

### 3.3 Google Cloud alignment (Well-Architected AI/ML perspective, DOC)

| Pillar | What the framework asks | What we do |
|---|---|---|
| Security | Treat all AI inputs as untrusted; screen prompts and responses with Model Armor; least privilege; dedicated service accounts; audit and lineage | Model Armor on input, output **and tool results** (own `after_tool` hook, since the plugin skips them); agent identity that can propose but has no approval or signing role; ledger stays the governance record |
| Reliability | Timeouts, retries, circuit breakers, graceful degradation, fallbacks, SLOs and error-budget alerts, validate generative outputs against schemas | Honest labelled replay is our graceful degradation (RL-7); output envelope schema; SLOs from `lighthouse.md` M5 |
| Operational excellence | Evaluate before deploying, golden datasets, monitor groundedness and quality in production, version prompts and datasets, canary releases with rollback | Spec 022 gates; BigQuery analytics plugin; prompt lock (exists); Cloud Run revision traffic split |
| Cost | Right-size, attribute costs with labels and billing export, alert on spend, smaller models first | Model routing and context caching; BigQuery `maximum_bytes_billed` and job labels; cost per turn in telemetry |
| Performance | Load test concurrency, autoscale | Parallel tool calls, p95 target (M5), hot versus warm tier by freshness need |

**Serverless and event-driven mapping.** Pub/Sub topic per data product, then a Cloud Run ingest service (contract validation, DLQ), fanning out to hot state, a Pub/Sub **BigQuery subscription** for the warm tier (Storage Write API, dead-letter topic, at-least-once so deduplicate by event id downstream; DOC), and GCS Parquet with lineage. **Known tension:** the hot tier is in-process DuckDB, which is stateful and per instance, while Cloud Run scales horizontally. Honest answer for now: a single-instance hot-state service rebuilt from the warm tier on start, with `as_of` on every fact. This is pre-mortem risk P5.

### 3.4 Where BigQuery earns its place

| Use | Why | Guardrail |
|---|---|---|
| Warm tier and history | Briefs require time series and trend analysis; hot state evicts at 24 hours | Named parameterised tools only |
| Agent telemetry dataset | Lighthouse metrics by SQL, via the first-party analytics plugin | Redaction, allow-listed events, CMEK dataset |
| Flywheel outcomes (accept, edit, reject) | Labelled decisions for threshold calibration | Written from the ledger, not by the agent |
| Geo (GEOGRAPHY, `ST_*`, S2; no native H3) | Spatial tools, public reference layers | Entity and jurisdiction level only |
| BigQuery ML forecast and anomaly functions | Deterministic engines for numbers, labelled as model-derived | Counts as a deterministic engine under RL-1 only with uncertainty shown (INF) |
| **Not in the governed path:** Conversational Analytics and `ask_data_insights` | The LLM authors the query logic, bypassing the metric registry | Possible later as a clearly labelled exploration mode over curated views |

Agent Search is for unstructured documents (statutes, regulator guidance, partner policy) with passage citations. BigQuery vector search is for entity-adjacent text and is not needed for v1.

## 4. Recommended architecture

```
Cockpit (eios-web, Cloud Run) --ID token--> eios-api (Cloud Run, private)
   Firebase uid -> verified operator, role
        |
   ADK Runner embedded in the existing FastAPI app (never `adk web` or `adk api_server`)
        App plugins: ModelArmor | ToolScope | AnswerRender+ResidueCheck | BQ Analytics (redacting)
        Agents: one LlmAgent per workstation, tools selected by role
                (Workflow only for the action path and compliance hold)
        Tools:  governed tool port --> OMCP handlers (hot DuckDB) .......... now
                                   --> BigQuery named tools (Toolbox) ...... warm tier
                                   --> DiscoveryEngineSearchTool (Agent Search) .. documents
                                   --> propose_action --> Intent Hub --> KMS, Firestore, WORM
        Sessions: FirestoreSessionService (db eios-state), key = verified uid
Event path: sources -> Pub/Sub -> eios-ingest (Cloud Run) -> contracts, DLQ
                      -> hot state | BigQuery subscription | GCS Parquet + lineage
```

### Decisions (need you; recommendation first)

| ID | Decision | Recommendation | Why |
|---|---|---|---|
| A-2 | Runtime shape | `LlmAgent` per workstation plus plugins first; `Workflow` only for staging and compliance hold | Invariants RL-1 and RL-2 are control flow, but plugins already cover every agent; add graph where pause and resume is natural |
| A-3 | Where it runs | Embedded in `eios-api` on Cloud Run. No Agent Runtime in v1. Gemini Enterprise and A2A as an optional later channel. Split into its own `eios-agent` service when it gains any tool beyond propose or when a second channel is added | One trust boundary, Firebase identity and four-eyes already there. Agent Runtime would split identity (Gemini Enterprise passes an email, our four-eyes needs the Firebase uid) |
| A-4 | Tool port | Typed Pydantic contracts per tool (ADR-018), generated into ADK `FunctionTool`s; per-workstation toolsets of about 10 to 12 tools `[ASSUMPTION]`; MCP Toolbox for the BigQuery tier when the warm tier lands (spike S-TBX-1); OMCP as an MCP server only as a later adapter | MCP is a transport, not a design. Too many tools degrades selection |
| A-5 | Answer design | Reference-based envelope via `output_schema`: text with `{{fact:...}}` references, `proposed_actions`, `ui_commands`, `citations`. Deterministic renderer plus residue check as a plugin. Fail closed after the 3-cycle bound | Removes the correction loop (B10) and the regex auditor |
| A-6 | ADR-002 | ADK confined to `src/eios/agent/`; the model comes through a `BaseLlm` adapter in `llm_gateway/providers/`; model id stays in config | Keeps `open_decision_check` meaningful and ADK behind an anti-corruption boundary |
| A-7 | State | `FirestoreSessionService`, key is the verified uid, no long-term memory in v1 | Fixes B1 and B3; memory of investigator conversations is a PII decision we should not take by default |
| A-8 | ADK tool confirmation | Do not use it for approvals. Approval stays the second human on the governed shelf | ADK confirmation is a same-session pause; it carries no four-eyes identity binding (INF) |
| A-9 | Pins | `google-adk[gcp]==2.11.0`, `fastapi>=0.133,<0.142.2`, `opentelemetry-*<=1.42.1` (A0 PR) | Section 3.2. Cost: FastAPI and OpenTelemetry stay behind latest until ADK relaxes its cap |
| A-10 | LangGraph | Keep until parity on the ported conversation tests, then delete (B12) | Avoids a flag-day |

## 5. Pre-mortem

Assume it is three months later and the ADK stage disappointed. Most likely causes, ranked by likelihood times impact.

| # | What went wrong | Early signal | Mitigation | Owner spec |
|---|---|---|---|---|
| P1 | We migrated the framework and nothing measurable improved | After the build, M3, M5 and agreement look the same as before | Baseline first (spec 022 runs red on today's copilot); stop rule from `lighthouse.md` section 6 | 022 |
| P2 | The reference design is brittle: the model drops or misformats references; users ask for derived figures (ratios, deltas) | More than 10% of golden turns need a retry `[ASSUMPTION]`; stilted answers | Spike S-ADK-3 on golden questions before committing; deterministic `compare` tool or render operators for derived figures; typed envelope; fail closed rather than loop | 021 |
| P3 | Wrong tool choice because the surface is untyped and large (OMCP is name-dispatched with duplicates) | Trajectory score below target; model calls duplicate handlers | Typed contracts, one canonical tool per capability, per-workstation toolsets, trajectory eval | 023 |
| P4 | Indirect prompt injection through partner comms or ticket text: the Model Armor plugin skips tool results (DOC) | Adversarial suite finds a narrative manipulated by tool text | Screen free-text tool results in an own `after_tool` hook; mark them untrusted in the envelope; scope tool arguments to the caller's role and entity set in `before_tool`; adversarial suite is a release gate | 021, 022 |
| P5 | Serverless scaling meets a stateful hot tier: instances disagree, cold start rehydrates slowly | Same question, different answer by instance; long first request | Single-instance hot service for now; `as_of` and `data_origin` on every fact; measure rehydrate time (S-DATA-1); warm tier for history | 025 |
| P6 | The deployed system still serves fixtures, so "live" answers are not live (R1) | Acceptance step 7 of the lighthouse cannot be shown honestly | Facts carry `data_origin`; renderer prints it; no "live" claim before spec 025 | 021, 025 |
| P7 | Dependency churn: ADK 2.x moves, pins hold FastAPI and OpenTelemetry back, parts of the API are `[EXPERIMENTAL]` | Resolver failures on routine bumps; security advisories on pinned packages | Exact pin; everything behind `src/eios/agent/`; monthly review; Dependabot ignore rule with a note | 021 |
| P8 | Latency stays high (turns up to 50 to 65 s today `[ASSUMPTION]`) | p95 flat after migration | Per-stage timing first; parallel tool calls, context caching, flash for routing, thinking budget; stop rule: move work to deterministic tools | 022, 021 |
| P9 | Governance regression: user id from the body, the ADK dev server exposed, a tool that stages without the hub | Red-line suite fails or is not run against the new path | Port `test_no_autonomous_write` and `test_red_line_suite` before any runtime code; Runner only inside our FastAPI; security review | 022, 021 |
| P10 | PII or tokens reach analytics logs or the model | Raw identifiers in `agent_events` | `content_formatter` redaction, event allow-list, CMEK dataset; vault tokens only; salt fix (R2) already merged | 021 |
| P11 | Scope creep: Gemini Enterprise, A2A, Agent Runtime and geo at once | More than one spec in flight | One workflow end to end first; channels are spec 028, off the critical path | all |
| P12 | Model Armor fail-closed turns an API blip into a dead copilot | Spikes of `model_armor_blocked` with no policy match | Keep fail-closed (regulated); honest replay label covers it; alert on screening failures | 021 |
| P13 | Eval theatre: LLM judges that do not measure faithfulness, or golden sets from the same generator as the data | Judges pass answers the deterministic check fails | M3 is deterministic; ADR-015 splits and sealed set; human review of a sample | 022 |

## 6. Spec plan (spec-kit)

Numbers continue from 020. **Build order is not numeric order.** `021` keeps the number CLAUDE.md already reserves for the ADK migration.

| Build order | Spec | Title | Why this position |
|---|---|---|---|
| 1 | 022 | Agent quality gates | Eval before build: golden questions, faithfulness metric, trajectory and adversarial suites, red-line port, telemetry; runs red against today's copilot and produces the baseline |
| 2 | 023 | Governed tool port and context schemas | Typed contracts for the tools the lighthouse needs first; retires `tools.py` fixtures; per-context schemas (R4) |
| 3 | 021 | ADK agent runtime | The migration itself, on the port and the gates |
| 4 | 024 | Knowledge retrieval | Agent Search corpus, citations, optional grounding check |
| 5 | 025 | Deployed event-driven data path and warm tier | Makes "live" true (R1, R5, R6); Pub/Sub, Cloud Run ingest, BigQuery subscription |
| 6 | 026 | Geo standard and reference layers | Shared columns on located objects; Overture, World Bank and FATF layers with provenance |
| 7 | 027 | Agentic GIS workstation | Spatial tools and map commands, built on 021 and 026 |
| 8 | 028 | Channels (optional) | A2A and Gemini Enterprise registration, OMCP as an MCP server |

### Spec scopes (what `/speckit-specify` should receive)

**022 Agent quality gates.** P1 faithfulness: every figure resolves to a tool result field (M3, seeded by the 13 cases in `test_auditor_known_gaps.py`), as an ADK custom metric. P2 trajectory: allow-listed tools, bounded rounds, correct refusal when data is missing. P3 adversarial: injection through tool text, four-eyes bypass, unauthorised write. P4 baseline report: M3 and M5 on today's copilot, and the M1/M2 timed-study protocol. GCP: `adk eval`, BigQuery analytics plugin, Cloud Trace.

**023 Governed tool port.** P1 port interface plus the first typed tools for the AML dossier flow (dossier, ring graph, structuring alerts, withdrawal risk, SAR draft, propose action). P2 per-workstation toolsets and markings enforced at the port. P3 retire the duplicates and the fixture module. P4 per-context schemas, governance tables out of the analytics DuckDB (R4). GCP: none new; defines the seam for BigQuery and Toolbox.

**021 ADK agent runtime.** P1 one grounded, reference-rendered answer on the AML workstation, with `data_origin`, honest replay and the 3-cycle bound. P2 verified-identity sessions on Firestore (B1, B3, B4). P3 workstation agents for partner manager, executive, compliance, operations. P4 governed propose-action wired to the intent hub and the browser shelf (A5). P5 delete LangGraph (B12). GCP: ADK, Gemini via the provider adapter, Firestore, Model Armor, BigQuery analytics. Supersedes ADR-016; new ADR for A-2, A-3, A-5, A-6.

**024 Knowledge retrieval.** Corpus decision first (D-3: which regulators), then ingestion into Agent Search, passage citations in the envelope, refusal when nothing is retrieved. GCP: Agent Search, Discovery Engine tool, optional Check Grounding.

**025 Data path.** Terraform for ingest service, topics, DLQ, BigQuery subscription tables, `EIOS_HMAC_SALT` in Secret Manager; single-instance hot service rebuilt from warm; freshness-based tier choice (D-2). GCP: Pub/Sub, Cloud Run, BigQuery, GCS, Secret Manager. Skills for the infra work: `gcp-devkit:terraform-gcp`, `cloud-run-deploy`, `iam-audit`, `firestore-rules`.

**026 and 027** are scoped after 021 lands, from `data-strategy.md` sections 6 to 8.

### Spikes (cheap, before the specs that depend on them)

| ID | Question | Needed by | State |
|---|---|---|---|
| S-ADK-1 | ADK tool loop, plugins and first-party integrations on Python 3.14 | 021 | Done, RUN |
| S-ADK-2 | Live Gemini via the global endpoint: parallel tool calls, thinking budget, `output_schema` with tools | 021 | Not run; needs `GOOGLE_CLOUD_QUOTA_PROJECT` set to an EIOS project (current gcloud project is the legacy `spatial-cat-489006-a4`) |
| S-ADK-3 | Reference-resolution rate and retry rate on about 30 golden questions | 021 go/no-go | Not run; needs spec 022 P1 |
| S-TBX-1 | MCP Toolbox: Python SDK on 3.14, Cloud Run service identity, offline stand-in for tests | 025 | Not run |
| S-DATA-1 | Hot-state rehydrate time from Parquet and from BigQuery | 025 | Not run |

## 7. Decisions recorded 2026-10-14

You approved: the build order and renumbering (section 6); embedding the agent in `eios-api` on Cloud Run (A-3); the reference-based answer design with a typed envelope, failing closed (A-5); and bounded live-Gemini spikes against an EIOS project. For the regulator corpus (D-3) the rule you set is: choose the use case with the best value that has publicly attainable data, which spec 024 applies when it is specified. A-2, A-4 and A-6 to A-10 proceed on their recommendations, since no objection was raised; A-9 (the dependency pins) was approved on 2026-10-14 once the A0 PR evidence was in. Spec 022 is being specified first.

## 8. Remaining open items for you

1. Approve the build order and the renumbering (section 6), or reorder.
2. Decisions A-2, A-3, A-4, A-5 (section 4). I would proceed on the recommendations unless you object.
3. Which regulators for the corpus (D-3), and whether the lighthouse M4 bar and stop thresholds are yours to set (`lighthouse.md` section 9).
4. Permission to run live-Gemini spikes against an EIOS project (a small, bounded bill).

## 9. Sources

- ADK 2.11.0 package source (read locally): `integrations/firestore`, `integrations/bigquery`, `integrations/model_armor`, `plugins/bigquery_agent_analytics_plugin.py`, `tools/discovery_engine_search_tool.py`, `tools/set_model_response_tool.py`, `workflow/`, `evaluation/`.
- ADK docs (via Context7 and adk.dev): graphs and routes, tool confirmation, safety callbacks, evaluation, sessions and state, built-in tool limits and `bypass_multi_tools_limit`, Model Armor plugin, A2A, Cloud Run deployment.
- Google Cloud docs: Well-Architected AI/ML perspective (security, reliability, operational excellence, cost pages); Pub/Sub BigQuery subscriptions; Gemini Enterprise "Register and manage ADK agents hosted on Agent Runtime".
- Third-party or secondary (UNV): William Denniss, "Deploying an ADK agent for Gemini Enterprise: Agent Runtime or Cloud Run?"; search-result summaries of Gemini Enterprise release notes and Agent Search pricing.
- The Developer Knowledge MCP rejected its API key throughout this session, so no claim here rests on it.
