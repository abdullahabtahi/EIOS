# EIOS Agent Architecture and Tool Use Cases

**Status**: DRAFT for review, nothing built. **Updated**: 2026-10-14. **Companions**: `adk-research.md` (decisions A-2..A-10, pre-mortem), `adk.md`, `lighthouse.md`, ADR-018, `specs/022-agent-quality-gates`.
**Evidence tiers**: **SRC** read in our code or the ADK 2.11.0 package; **RUN** executed; **DOC** read in documentation; **INF** my inference; **GAP** does not exist yet.

> The agent is a thin, governed interface over deterministic engines. It selects tools, assembles evidence, drafts, and proposes. It never computes, scores, approves or writes.

---

## 1. What the agent is for (jobs, not features)

Tools follow the operator's jobs. Each job below is worded from the briefs (`[BRIEF]`) and mapped to who does it, what the agent contributes, and what stays deterministic.

| Workstation | Job | Agent contribution | Stays deterministic |
|---|---|---|---|
| AML investigator | Triage about 2,000 alerts a week into the few worth a human (`monitoring.md`) | Narrate why the top cases rank where they do; pre-assemble dossiers overnight | Detection, scoring, ranking, hub suppression |
| AML investigator | Decide one alert: assemble context from 5+ systems and reconstruct the timeline | Gather facts through tools, cite them, show counter-evidence and the causal label | Every figure, the graph, the causal gate |
| AML investigator | File an STR/SAR in time | Draft the narrative from resolved facts, cite the rule that applies to the entity's licensing jurisdiction | Figures; the filing decision stays human |
| AML investigator | Stop a bad withdrawal | Propose a hold with evidence references | Signing, four-eyes approval, ledger |
| Partner manager | Know which partners need attention this week (`churn.md`) | Rank and explain drivers; connect tickets, commission disputes and activity decay | Churn scores, cohort statistics |
| Partner manager | Check whether a partner is gaming commissions (`fraud.md`) | Assemble ring, opposite-trade and referral evidence | Detection, graph, attribution |
| Partner manager | Act on a finding | Draft outreach or propose a commission review | Approval |
| Executive | Understand why a metric moved across domains (`data.md`) | Synthesise governed metrics, causal evidence and forecasts into a briefing | Metrics, forecasts, scenario engine, causal gate |
| Executive | Ask "what if" | Translate the question into scenario shocks, narrate the result | The 200 ms parametric engine (RL-6) |
| Compliance auditor | Prove the decision trail | Explain ledger state in words | Hash-chain verification |
| Data operations | Keep the pipeline healthy | Explain an incident from the data-quality board | SLOs, DLQ, redrive |

**Where the agent adds the most value** (INF): dossier assembly with citations and SAR drafting (time saved, measured by lighthouse M1 and M2), and the pre-assembled overnight dossier for the top-ranked alerts. **Where it adds the least**: compliance and operations, which are mostly deterministic views, so they get small read-only explainers.

## 2. Tool catalogue

### 2.1 Design rules

1. **Task-oriented, not CRUD.** One tool per question an operator asks, not one per table.
2. **Typed in, typed out.** Pydantic contracts; no free-text arguments to data tools. Entity ids come from earlier tool results or session context.
3. **Every result is a fact bundle.** Each value carries a stable `fact_id`, a unit, an `as_of` time, its `data_origin` (fixture or live), a provenance pointer and its security marking. The answer renderer resolves references against these (spec 021).
4. **Typed errors.** `NOT_FOUND`, `FORBIDDEN_MARKING`, `DATA_UNAVAILABLE`, `STALE`. The agent must refuse honestly on each; none lets it invent.
5. **About 10 or fewer tools per agent** `[ASSUMPTION]`. Large flat tool lists degrade selection; scope by workstation.
6. **Untrusted text is marked.** Partner messages, ticket bodies and any document text return with `untrusted: true`, structured fields first, bounded excerpts second.
7. **Read, draft, propose. Never approve or execute.** `approve_action` and `execute_action` exist in OMCP (SRC) and are never in any agent's toolset; a safety test asserts that.

### 2.2 Catalogue (target names; "From" is today's OMCP handler)

Kinds: **E** evidence read, **K** knowledge search, **C** deterministic compute, **D** draft, **P** propose, **V** view command.

| Scope | Tool | Kind | From (SRC) | Notes |
|---|---|---|---|---|
| Shared | `get_metric` | E | `get_metric`, `list_metrics`, `get_metric_provenance` | One governed number with unit, as-of, definition |
| Shared | `resolve_entity` | E | `get_entity` | Canonical id and type; anchors follow-ups |
| Shared | `get_causal_evidence` | E | `get_causal_chain` | Returns "verified causal" or "Correlation Only" (RL-3) |
| Shared | `compare_facts` | C | **GAP** | Delta, ratio, percentage between two facts. Needed because the model may not do arithmetic; closes pre-mortem P2 |
| AML | `list_alerts` | E | `get_workstation_view`, `get_roundtrip_structuring_alerts` | Ranked queue with reason codes |
| AML | `get_aml_dossier` | E | `get_aml_entity_dossier` (retire `get_client_aml_dossier`) | The one-screen evidence bundle |
| AML | `get_network_evidence` | E | `get_mule_ring_graph`, `get_kinetic_network_graph`, `traverse_graph` | With CGNAT hub suppression (RL-4) flagged |
| AML | `get_activity_timeline` | E | **GAP** (dossier may include one; unverified) | Trades, deposits, device and IP events in order; the brief's "reconstruct the timeline" |
| AML | `check_withdrawal_risk` | E | `check_withdrawal_risk` | |
| AML | `search_regulations` | K | **GAP** (today a fake `query_policy_search`) | Agent Search, filtered by jurisdiction; passage citations |
| AML | `draft_sar` | D | `compose_sar_draft` (retire `generate_sar_draft`) | Structured sections; text refers to facts |
| AML | `propose_hold` | P | `propose_aml_action` | Stages an intent; hub signs and awaits a second human |
| Partner | `list_partner_worklist` | E | `get_high_risk_cohorts`, `get_churn_radar_scatter` | Ranked by risk times value |
| Partner | `get_partner_signals` | E | `get_partner_signals` | Behavioural, financial, relationship signals |
| Partner | `get_partner_integrity` | E | `get_partner_fraud_dossier`, `get_opposite_trading_pairs`, `get_partner_referral_ring`, `get_ring_evidence` | Observed facts only; no accusation |
| Partner | `get_client_quality` | E | `get_client_quality_profile` | |
| Partner | `read_partner_comms` | E | `search_comms` | **Untrusted text.** Structured topic and date fields, bounded excerpts |
| Partner | `search_policy` | K | **GAP** | Commission and programme policy (synthetic documents) |
| Partner | `propose_partner_action` | P | `propose_action` | Typed action kinds: commission review, retention playbook, integrity escalation |
| Executive | `get_briefing` | E | `get_morning_briefing`, `get_briefing` | |
| Executive | `get_forecast` | E | `get_forecast` | |
| Executive | `run_what_if` | C | `simulate_what_if_shock` (retire `run_scenario`) | Parametric propagation, attribution sums to 100% (RL-6) |
| Executive | `get_cohort_trend` | E | **GAP** (needs the warm tier, spec 025) | History by region and cohort |
| Executive | `get_market_context` | E | **GAP** (needs reference products, spec 026) | |
| Compliance | `get_ledger_timeline`, `get_intent_status`, `get_audit_status` | E | `get_ledger_timeline`, `get_intent_status`, `get_ledger_audit_status` | Read and explain |
| Compliance | `verify_chain` | E | `verify_hash_chain` | The check is deterministic; the agent reports it |
| Operations | `get_dq_board`, `get_reliability`, `get_drill_status`, `get_calibration_status` | E | the four matching handlers | Read and explain |

Counts per agent: AML 11, partner 8, executive 8 (shared tools included), compliance 4 to 6, operations 4 to 6. AML is the largest and is the first to need splitting if selection quality drops (decided by the trajectory suite, spec 022).

**Surface hygiene (spec 023).** OMCP has 42 handlers (SRC); about eight are duplicates or overlaps (`get_client_aml_dossier`/`get_aml_entity_dossier`, `generate_sar_draft`/`compose_sar_draft`, `get_briefing`/`get_morning_briefing`, `run_scenario`/`simulate_what_if_shock`, three graph tools, two chain-verify tools). Today's copilot exposes a different, smaller fixture set (`get_governed_metric`, `inspect_aml_entity`, `query_graph_topology`, `inspect_partner_churn`, `run_causal_what_if`, `stage_action_intent`) plus two fake retrieval tools. The port replaces both with the one typed catalogue above.

## 3. Agent topology

```
Cockpit command bar --(verified uid, role, workstation, entity context)--> eios-api (Cloud Run)
        |
   Gateway: identity, session key = uid + thread, rate limit, data_origin
        |
   ADK App ------------------------------------------------------------------------------+
   | Plugins (wrap every agent):                                                          |
   |   InputGuard (Model Armor)  ToolOutputGuard (Model Armor on tool results, adapted    |
   |   from the safety-plugins recipe)  ToolScope (allow-list, role, entity scope)        |
   |   FactLedger (assigns fact ids)  AnswerRender (resolve refs, residue check,          |
   |   fail closed)  Telemetry (BigQuery analytics, redacted)  HonestReplay               |
   |                                                                                      |
   | Workstation agents (LlmAgent, one per role, selected deterministically from role):   |
   |   aml_investigator | partner_manager | executive | compliance | operations           |
   |   Sub-agents as AgentTool:  regulation_researcher (Agent Search)                     |
   |                             sar_drafter (typed sections, refs only)                  |
   | Deterministic graph (Workflow): action staging path, compliance-hold arbitration     |
   +--------------------------------------------------------------------------------------+
        |  tool port (typed contracts)
        +--> OMCP handlers over hot state (now)   +--> BigQuery named tools (warm, spec 025)
        +--> Agent Search (documents, spec 024)   +--> Intent Hub (propose only) --> KMS, Firestore, WORM
```

Choices and reasons:
- **Routing by role, not by LLM.** The role and workstation are known from the verified session; an LLM router adds latency and a failure mode for no gain (INF). The keyword supervisor goes away.
- **One agent per workstation**, not one for everything: smaller toolsets, tailored instructions, independent evals. Cross-domain questions are the executive agent's job, using synthesis tools rather than delegating to domain agents (v1).
- **Sub-agents only where context isolation pays**: retrieval (long passages stay out of the main context) and SAR drafting (separate prompt and schema).
- **Graph where control flow is the contract.** Staging an action and arbitrating a compliance hold are deterministic, so they are `Workflow` nodes, not prompts (A-2).
- **Embedded, not a separate service** (A-3). Split when the agent gains any tool beyond propose.

## 4. The ambient path (event-driven)

The highest-value use of an LLM here is not chat. It is making the dossier exist before the investigator opens the alert. The `ambient-expense-agent` recipe (SRC, cloned) shows the pattern: a Pub/Sub event reaches an ADK trigger endpoint, rules in code route it, and only cases that need judgement reach the LLM.

```
alert event --> Pub/Sub (push, OIDC, dead-letter) --> trigger endpoint in eios-api
   --> deterministic score and rank (existing detectors)       [rules in code]
   --> top N only: dossier assembly through the same tool port [LLM, references only]
   --> cached dossier in Firestore, shown instantly in the triage rail
   --> investigator acts; approval is the governed shelf (intent hub), never an LLM
```

This makes lighthouse M6 ("2,000 alerts into 50 cases") a pipeline and M1 (time to disposition) a pre-computation. It is serverless and event-driven in the Google Cloud sense: Pub/Sub, Cloud Run, nothing idle. The ADK trigger and the human pause in that recipe (`RequestInput`) are not used for approval; ours is the intent hub, which already carries KMS signing and four-eyes (INF, A-8).

## 5. Knowledge corpus (acquired 2026-10-14)

Rule you set: the best-value use case with publicly attainable data. The use case is **citing the applicable rule and red-flag typology in an AML disposition and SAR draft, per licensing jurisdiction**. Manifest: `EIOS/data/corpus/regulatory/manifest.yaml` (checksums, pages, versions, licence state).

| Document | Jurisdiction | State |
|---|---|---|
| FIAU Implementing Procedures Part I (last amended 27 April 2026, 313 pages) | Malta | Acquired, text layer |
| Prevention of Money Laundering and Funding of Terrorism Regulations (S.L. 373.01, 51 pages) | Malta | Acquired, text layer |
| Labuan FSA Guidelines on AML/CFT/CPF and TFS for Labuan KRIs (2025, 155 pages) | Labuan | Acquired, text layer |
| Labuan FSA Guidance Note on Red Flag Indicators for Digital Financial Services (24 June 2024, 6 pages) | Labuan | Acquired, text layer |
| Labuan FSA Circular on Red Flag Indicators for Labuan IBFC (2024, 2 pages) | Labuan | Acquired, **image only, needs OCR** |
| FinCEN SAR narrative guidance (2003, 33 pages) | US | Acquired, public domain; structure reference only |
| FATF Recommendations | International | **Not acquired**: scripted download returned 403 and I did not work around it. Manual download needed |

**Open, and I can't close it from here:** reuse terms. The only retrievable FATF terms page covers data, not publications; FIAU, Labuan FSA and legislation.mt terms were not retrievable. The manifest therefore says `unverified`; the PDFs are git-ignored; the corpus is for a private retrieval index with short attributed quotations. Before the public demo shows more than that, confirm terms or ask the regulators (decision D-3, yours).

Deriv's licensing entities are from third-party listings and are recorded as `[ASSUMPTION]` pending the MFSA, FIAU and Labuan FSA registers.

**How it will be used (spec 024):** a Cloud Storage bucket, a managed Agent Search data connector (the `rag-agent-search` recipe), per-document metadata (jurisdiction, kind, version) so retrieval can be filtered to the entity's regulator, passage-level citations in the answer envelope, and an honest refusal when nothing is retrieved. The agent never quotes a rule from memory.

## 6. Recipes to lift and the scaffold decision

| Need | Recipe (cloned, SRC) | Lift |
|---|---|---|
| Tool-output screening, session-poisoning defence | `safety-plugins` | The Model Armor plugin's `after_tool` screening and the user-message halt. This fills the gap in ADK's built-in plugin |
| Event-driven triage with rules in code | `ambient-expense-agent` | Pub/Sub trigger wiring, `pubsub.tf`, dead-letter, the router-then-LLM graph |
| Regulator RAG | `rag-agent-search` | Bucket, connector scripts, Terraform, the `VertexAiSearchTool` seam and its test double |
| Production quality monitoring | `ambient-quality-agent` | Later: scheduled evaluation of live turns from the telemetry table |
| Guard chain, exfiltration detection, sub-agent isolation | `long-horizon-harness` | To study in spec 021; not read in depth yet |

**Scaffold decision.** I generated a reference project (`agents-cli scaffold create`, Cloud Run, GitHub Actions) in the scratchpad and read it. I do **not** recommend running `scaffold enhance` on this repository: it would add an `app/` directory, its own Dockerfile and a second CI/CD and Terraform tree beside ours, which already deploys through Cloud Build with a least-privilege identity (CLAUDE.md section 7). We borrow instead: the eval layout and `custom_function_file` metric pattern, the telemetry Terraform (`telemetry.tf`, the GenAI logs schema), and the A2A wiring if a channel is ever added. Tell me if you would rather scaffold a separate `eios-agent` service now; that is the same split as decision A-3 but earlier.

## 7. What this changes in the specs

- **022**: golden cases and the trajectory suite are defined against this catalogue (expected tools per job), and a safety test asserts the agent toolset never contains `approve_action` or `execute_action`.
- **023**: builds the catalogue in section 2 in priority order: the AML flow first (it is the lighthouse), then partner, then executive.
- **021**: the topology in section 3; plugins in the order shown.
- **024**: the corpus in section 5.
- **025**: adds `get_cohort_trend` and the event-driven path in section 4 beyond the hot state.

## 8. Decisions recorded 2026-10-14

1. **Corpus use case**: confirmed (cite the applicable rule and red-flag typology in AML dispositions and SAR drafts, per jurisdiction).
2. **FATF Recommendations**: left out of v1 (user).
3. **Reuse terms**: not a blocker for this non-commercial prototype (user); the manifest still records them as unverified and the corpus is not redistributed.
4. **Overnight pre-assembled dossiers**: **deferred to after spec 021** (my decision, the user asked me to choose). Reasons: (a) lighthouse M1 has no measured baseline yet, and adding the largest M1 lever before the baseline would make any before-and-after comparison unattributable; (b) it needs the deployed event-driven data path (data-strategy R1, spec 025) to be honest rather than fixture-backed; (c) it should reuse the typed tool port and the reference-answer renderer, which only exist after specs 023 and 021. It gets its own spec (029, ambient dossiers) once the ADK runtime proves faithful answers on the baseline.

## 9. Frontend direction (input to spec 030, agent workspace UX)

**User preference (2026-10-14).** Inside the existing dossier pane, a switch between the dossier and a chat view; the command-bar button opens that chat view instead of a modal. The quick wording and data fix I proposed was deferred by the user to stay in the ADK spec lane; it is listed here so it is not lost.

**What the user reported**: the Cmd+K modal blocks the workstation, so the assistant feels separate; the on-screen wording is internal jargon; `DISPATCH_RETENTION_PLAYBOOK` is meaningless to an operator.

**What the code shows (SRC, 2026-10-14)**
- The workstation shows churn hazard 78% and login drop 68% for PTR-882 (`src/eios/cockpit/partner.py`); the copilot's partner tool returns 0.84, a 62.4% decay and a named rival as constants for any partner id (`src/eios/conversation/tools.py`). The assistant cannot agree with the screen because it reads different data.
- The suggested action is a literal string in `src/eios/conversation/copilot_engine.py`, unrelated to the question or to the Concession Simulator in the dossier. The workstation already has real retention deals (`RetentionPlaybookDeal`: title, estimated cost, projected uplift, whether a second approver is needed) that the proposal should be built from.
- Partner ids drift between layers: the radar and triage use `PTR-882`, the backend dossier endpoint and the copilot use `AP-1029` and `P-882` for the same story.
- The browser sends `activeEntityId` but the server reads `context_entity_id`, so the assistant never learns which entity is on screen (defect B2).
- Internal labels shown to operators: "Principle I & III: Zero unanchored claims", "Qualitative Pass", "AIP Logic · Gemini 3.8 Flash (Dual-Verified)", "TIER_1_SUPER", a per-chip "[ILLUSTRATIVE]" tag, "Stage to Shelf".

**Requirements for spec 030**
1. The assistant reads the same objects the cards show (one governed read path, spec 023) and can see the operator's selection and filters.
2. The assistant can operate the view (select, filter, highlight, set the simulator), visibly and with undo; it can never change data except by proposal.
3. Plain operator language; trust shown by exception (a failed check, a saved answer, demo data), details on demand.
4. Proposals read as: what, to whom, how much, expected effect with range, who must approve. Built from the real deal data, not a canned name.
5. Retire the modal. The dossier gets a Dossier and Chat switch as the user prefers; the command-bar button opens the chat view.

**Trade-off to design around.** With a switch, figure chips cannot highlight their source card while chat is showing. Mitigation to specify: chips carry the value, unit and as-of inline; "show in dossier" flips back and highlights the card; the chat view pins a one-line context strip (entity, key figures, data origin); a Focus expand is the only other mode.

**Gate added to spec 022**: FR-026 and SC-011 check that the agent's figures agree with the workstation's, so spec 023's fix is provable.
