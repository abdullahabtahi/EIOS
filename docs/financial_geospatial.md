# EIOS Product Strategy & Plan v3: The Regulator-Grade AML Investigator

**Version**: `3.0.0` (supersedes `2.0.0`, an engineering-first draft)
**Date**: `2026-10-13`
**Status**: `DRAFT FOR REVIEW. Strategy and plan only; no specs, ADRs or code for the items below have been written.`
**Audience**: the team, hackathon judges, and an investor reading cold. Read section 0 first.
**Provenance tags**: `[BRIEF]` canonical requirement (`docs/brief/*`), `[ASSUMPTION]` a number we chose and must validate, `[ILLUSTRATIVE]` worked example, `[TARGET]` a commitment we will measure, `[SPIKE]` a technical claim from a time-boxed spike, `[EXTERNAL]` a third-party claim with a source link in section 13 (secondary sources are marked; verify before formal use), `[MEASURED]` reserved for results we actually produce.

---

## 0. The one-page version

**Problem.** Anti-money-laundering (AML) teams drown in alerts that are almost all noise, and the work of clearing them is slow, manual and spread across five or more systems `[BRIEF monitoring.md: ~2,000 alerts/week, ~95% false positives, 5+ systems]`. The false-positive rate is widely reported at 90-95% `[EXTERNAL, secondary]`. Every alert costs analyst minutes. A reportable case then costs hours more to write up as a suspicious activity report (SAR). Regulators expect it done, documented and explainable, and US institutions file millions of SARs a year `[EXTERNAL]`.

**Who hurts and who pays.** The investigator feels it daily; the head of compliance (MLRO) is accountable to the regulator and owns the budget. Mid-market brokerages, crypto exchanges, payment and cross-border fintechs have the volume and the obligation but cannot staff like a Tier-1 bank.

**Solution.** EIOS is an investigation copilot that clears an alert in minutes, not by being a smarter black box, but by being **auditable**: every figure in its narrative is traced to a deterministic tool result, every consequential action needs two signed human approvals, and every answer ships with an evidence bundle a regulator can replay.

**Why now.** LLM agents are finally good enough to do the reading and drafting `[SPIKE: live answers passed the numeric audit 4 of 4 after fixes]`, and regulators are converging on explainability, governance and an audit trail of both the AI recommendation and the human decision `[EXTERNAL, secondary]`. Buyers will adopt AI faster if it comes with proof.

**Why us, honestly.** The "AI investigator" category is already funded and crowded (section 4). Governance alone is a feature competitors can copy. Our durable edge has to be (a) proof-carrying output that survives a regulator, and (b) a data flywheel: every analyst decision becomes a labelled outcome that improves triage for that customer. Section 5 says how, and section 11 says what would prove us wrong.

**What we build first.** One wedge: *alert triage plus SAR draft*, for one persona, measured against one baseline. Geography is an **evidence lens inside the investigation** (jurisdiction risk, IP-versus-KYC country, cross-border corridors, offshore-structure precedent). It is not the product.

**The ask of this plan.** Prove three numbers with real or realistic cases before adding any breadth: minutes per alert, SAR drafting time, and accuracy of recommended dispositions against human decisions (section 6).

---

## 1. The problem, quantified honestly

### 1.1 What is known
| Fact | Source |
|---|---|
| ~2,000 alerts a week, ~95% false positives, 5+ systems to pull context from | `[BRIEF monitoring.md]` |
| 90-95% of transaction-monitoring alerts are reported false positives (vendor and industry commentary; trace to the primary study before formal use) | `[EXTERNAL, secondary]` |
| FinCEN received about 3.8M original SARs in calendar 2024 and about 4.7M in fiscal 2024 (different periods; cite FinCEN directly); the top 10 filers account for about 45% | `[EXTERNAL]` |
| Regulators stress explainability, model governance, record-keeping and human accountability for final SAR decisions | `[EXTERNAL, secondary]` |

### 1.2 The cost of the status quo, as a model you can check
Cost per year = alerts per week x 52 x minutes per alert / 60 x loaded hourly cost.
`[ILLUSTRATIVE]` with the brief's volume and our assumptions: 2,000 x 52 x 20 min / 60 x $60/h `[ASSUMPTION: 20 min and $60/h are placeholders to replace with design-partner data]` is about $2.1M a year of triage labour for one mid-size team, before SAR writing, rework and regulator findings.
Savings case: if triage time falls 60% `[TARGET]`, the same team recovers about $1.2M a year. A fair price is a fraction of that (section 9). **Every number above is a hypothesis until a design partner replaces it.**

### 1.3 Why the pain recurs
Alert volume is continuous and grows with the business; SAR obligations are legal; staff turnover resets institutional knowledge; regulators audit repeatedly. This is a daily, mandatory, budgeted workflow, which is the shape of a product people pay for.

---

## 2. Customer and wedge

| | |
|---|---|
| **Ideal first customer** | Mid-market online brokerage, crypto exchange or cross-border payments firm with an in-house AML team of roughly 5-50 `[ASSUMPTION]`, real alert volume, and no appetite for a multi-year Tier-1 platform rollout |
| **User** | AML investigator (clears alerts, drafts SARs) |
| **Buyer** | MLRO / Head of Compliance, with the CFO or COO as budget holder |
| **Wedge workflow** | Level-1 and Level-2 alert triage, evidence assembly, SAR narrative draft, dual-approved action (hold or freeze) |
| **Expand later** | Case management, sanctions and adverse-media screening, partner/affiliate fraud and churn (the other briefs), cross-customer typology sharing under privacy constraints |

**What we are not building:** a map product, a CARTO clone, or a general chatbot.

---

## 3. Product: "Close an alert in three minutes"

### 3.1 The flagship demo (also the real workflow)
An investigator opens alert `CR84920`, a synthetic account `[ILLUSTRATIVE]`.
1. **Brief, not a blank page.** The copilot reads the alert and assembles the dossier: KYC claim versus realized activity, counterparties, device and IP clusters, ring structure with shared-gateway suppression (RL-4). Each figure links to the tool call that produced it.
2. **Evidence lenses.** Behavioural signals (velocity, round-trip patterns), **geographic signals** (IP country versus KYC country, impossible travel, cross-border corridor, jurisdiction risk), ownership and offshore-structure precedent from public reference data, and sanctions screening. Each lens is deterministic; the model narrates.
3. **Recommendation with uncertainty.** Disposition suggestion with confidence and the strongest counter-evidence; "Correlation Only" where causal claims fail the gate (RL-3).
4. **SAR draft** with every number cited, statutory references normalized, ready for human edit.
5. **Action.** Staging a hold or freeze creates a KMS-signed intent that needs two distinct approvers (RL-2); the ledger entry is hash-chained (RL-5).
6. **Proof.** A "verify" control re-walks the ledger and replays the evidence bundle.
7. **Timer.** The demo shows the same case done manually across five tools versus in EIOS, with the clock visible.

### 3.2 The geographic lens, concretely (deterministic signals, no LLM math)
- IP-derived country versus KYC country mismatch; impossible-travel velocity between logins.
- Cross-border corridors: flows aggregated by origin and destination jurisdiction, with jurisdiction risk tiers from published lists `[to verify: FATF lists]`.
- Offshore-structure precedent: how often a jurisdiction chain like this one appears in a public leak dataset (counts only; see data policy).
- Presented on a light Google Maps canvas with deck.gl; clicking a mark opens the existing Entity 360 inspector. The map earns its place only where it shortens an investigation; if a lens does not, cut it.

### 3.3 UX principles
Glass-box timeline of what the agent did; proof chip on every answer; map as a lens on ontology objects; honest degradation (a replay is always labelled, RL-7); light analytical surfaces and two-header maximum per `EIOS/web-prototype/CLAUDE.md`.

---

## 4. Competition and defensibility

| Player | What they are | Our difference |
|---|---|---|
| Bretton AI (formerly Greenlite) | AI-agent AML investigations; reported $75M Series B, February 2026, with Robinhood and Mercury among customers `[EXTERNAL, secondary]` | The most direct competitor. We must beat them on provable correctness and auditability, not on "has an agent" |
| Hawk AI, Unit21, Sardine, ComplyAdvantage, Featurespace, Feedzai | Detection and case platforms with AI features; several well funded `[EXTERNAL, round details conflict across sources]` | They sell detection and workflow; we sit on top as the investigation layer and consume their alerts |
| Quantexa | Entity resolution and network analytics for large institutions | Heavy, Tier-1; we target mid-market speed to value |
| Legacy suites (NICE Actimize and similar) | Incumbent rules-based monitoring | Slow and opaque; the thing buyers want to augment |
| Chainalysis, Elliptic | Crypto blockchain analytics | Complement, not replace, for crypto buyers |

**Where defensibility really comes from (ranked, honestly):**
1. **Decision flywheel.** Each analyst accept, edit or reject is a labelled outcome in our ledger. Over time, per-customer triage priors and typologies improve, and switching means losing that history. This is the real moat and it needs real usage to exist.
2. **Proof-carrying output.** Hallucination rate measured at zero numeric mismatches by a deterministic auditor, plus signed dual control and replayable evidence. A competitor can copy the idea; matching a measured, regulator-shaped track record takes time.
3. **Ontology and integration depth.** Per-customer mapping of their alerts, accounts and counterparties into one governed ontology.
4. *Not a moat:* using Gemini, using MCP, having a map.

---

## 5. Evidence we will produce (so the pitch is not adjectives)

The biggest weakness of an AI-for-compliance claim is that nobody can verify it. Our counter is a **backtest harness**: run the copilot on a labelled set of past alerts and report, with confidence intervals, how often its recommended disposition matches the human decision, how fast, and whether any figure was unsupported.

| Headline metric | Definition | Baseline | Target | How measured |
|---|---|---|---|---|
| M1 Time to disposition | Median minutes from alert open to a justified disposition | `[ASSUMPTION]` 20 min, to be replaced by a timed manual run on the same cases | -60% `[TARGET]` | Timed study with volunteer analysts on seeded cases, then design-partner data |
| M2 SAR draft time | Minutes to a reviewable SAR narrative | `[ASSUMPTION]` replace with measured | -70% `[TARGET]` | Same study |
| M3 Numeric faithfulness | Share of figures in output traceable to a tool result | n/a | 100% `[TARGET]` (enforced by the auditor, reported as `[MEASURED]`) | Hallucination eval, CI-gated |
| M4 Disposition agreement | Agreement with human disposition on labelled alerts | n/a | Set after the first backtest; never claimed before measured | Backtest harness |
| M5 Cost and latency per turn | Dollars and seconds per investigation turn | now 5-65 s depending on corrections `[SPIKE]` | p95 under 15 s `[TARGET]` | OTel, load test |

Public labelled data (for example a labelled illicit-transaction graph) can validate detector quality only if its licence allows; it carries no geography, so it cannot validate the map. The seeded synthetic cases carry the end-to-end story and are always tagged `[ILLUSTRATIVE]`.

---

## 6. Validation plan (do this alongside the build, not after)

1. **Ten discovery conversations** with MLROs and investigators at mid-market brokerages, exchanges and payments firms. Learn: current minutes per alert, tools, who signs off, what they would pay, what they fear about AI.
2. **Three design partners** willing to run in shadow mode on historical closed alerts (no production risk), giving us labelled data for M4.
3. **Pricing test:** per-investigator seat versus per-alert volume versus an outcome-linked tier; see section 9.
4. **Kill criteria** (stop or pivot if true after the design-partner phase): partners will not let an LLM touch their alerts under any controls; backtest agreement stays below the level an investigator would trust `[TARGET to set with partners]`; the economic buyer will not pay a fraction of the measured savings.

---

## 7. Architecture (re-baselined to what exists today)

### 7.1 Already built and deployed `[verified 2026-10-13]`
Public `eios-web` (Next.js) and private `eios-api` (FastAPI) on Cloud Run; Identity Platform sign-in with role claims; KMS-signed action intents through an intent hub; four-eyes enforced on verified identities; Firestore-backed ledger, approvals and nonces; honest API proxies; live Gemini copilot with a bounded, allow-listed tool loop and bounded self-correction; Terraform for the environment; CI with provenance, ADR and infra-policy gates.

### 7.2 To build, in this order
1. **Migrate the agent to Google ADK** (decision made). Keep: auditor egress scan, compliance-hold arbitration, human-in-the-loop interception that mints a KMS-signed intent, the allow-listed tool set, the 3-cycle bound. Fix: replace keyword routing with real routing; surface replay status to the UI; cut correction-round latency.
2. **Evidence tools** behind the existing OMCP tool port: geographic signals, jurisdiction risk, precedent counts, sanctions screening port.
3. **Reference data layer** (section 8).
4. **Backtest harness and eval flywheel** (section 10).
5. **Wire the browser's governed-action shelf to the real endpoints.** It is client-side state today; judges and buyers will click it.

### 7.3 Deliberate simplifications versus v2
- **Two services, not six.** Keep `eios-web` and `eios-api`; run the ADK agent inside the API until load or isolation forces a split. Add `market-data` (OpenBB) only if a scenario needs it.
- **No graph database until a spike justifies it.** Start with precomputed jurisdiction and ownership-chain tables in BigQuery; benchmark a graph backend only if multi-hop queries are slow. D-2 is a decision gate, not a plan.
- **Typed intent, deterministic compile** stays (the model proposes a structured query; code builds parameterized SQL from a registry of named metrics). It is the cleanest way to satisfy RL-1 for spatial and aggregate questions.

### 7.4 Operations (v2 omitted these)
| Concern | Plan |
|---|---|
| SLOs `[TARGET]` | Turn p95 under 15 s; API availability and error budget defined per month; separate budget for the agent path |
| Alerting | OTel metrics for agent latency, error rate, token spend and replay rate, alerts configured as Terraform (Google's agent-alerting guidance) |
| Cost control | Per-operator and per-day token caps, global kill switch, Gemini context caching for the long ontology prefix, model routing (a fast model for routing and drafting, a stronger one only when needed) |
| Abuse and safety | Rate limits per operator, Model Armor evaluated as a managed layer, all third-party and dataset text treated as untrusted input |
| Replay and evidence | Evidence bundles reference **BigQuery table snapshots with a retention policy**, not time travel (which is short-lived), so "replay" stays true for audit periods |
| Multi-tenancy | Single-tenant per customer in their own project first (buyers expect data to stay in their cloud); multi-tenant SaaS is a later decision |
| Security roadmap | Customer-managed encryption keys and VPC Service Controls for regulated buyers; disaster-recovery stance written before the first pilot |
| Permissions | Security markings on geo and reference data in the ontology, so a lens inherits the access rules of its objects |

---

## 8. Data policy and legal

### 8.1 Two layers
- **Customer private layer** (synthetic here, tagged `[ILLUSTRATIVE]`): accounts, partners, devices, IPs. In a real engagement this is the customer's data and stays in their project.
- **Reference layer** (public, governed): jurisdiction risk, ownership and offshore-structure reference, sanctions, geography, macro.

### 8.2 Sources and terms
| Source | Terms to respect | Use |
|---|---|---|
| ICIJ Offshore Leaks (entity and jurisdiction level only) | ODbL database, CC BY-SA contents: attribution, share-alike on derived databases, and a non-implication notice in the UI | Structural precedent counts; `[SPIKE]` 814,344 entities and 3,339,272 relationships in the 2026-09 dump. The leaks are historical, so use for structure, not as current ownership truth |
| GLEIF Level 2 | Terms to verify; accounting consolidation, not beneficial ownership | Corporate parent chains |
| OpenSanctions | CC BY-NC for bulk data; commercial use needs a licence | Hackathon only; production uses a pluggable screening port with official lists |
| Overture Maps (BigQuery public) | Check attribution terms | Divisions, places |
| Google Maps Platform | Platform terms (no scraping or caching of tiles) | Basemap with deck.gl overlay |
| OpenBB | AGPL: run unmodified in its own service; Dekart is AGPL, reference only | Macro and competitor market data, only if a scenario needs it |

### 8.3 Policies
- **P-1** No synthetic assertion about a real named entity. Fictional cases link to synthetic shells and to jurisdictions.
- **P-2** Entity and jurisdiction level only; no natural-person names or street-level geocoding.
- **P-3** Provenance on every row (source, licence, as-of) and an `[EXTERNAL]` tag, added by ADR.
- **P-4** Attribution and the non-implication notice wherever leak data appears.
- **P-5** Dataset text fields are untrusted prompt input.

---

## 9. Business model and go-to-market (hypotheses to test)

- **Pricing:** per investigator seat plus a volume tier `[ASSUMPTION]`; an outcome-linked option (price tied to measured hours saved) is attractive to a CFO and is worth testing. Anchor on a fraction of the savings in section 1.2.
- **Sizing method (fill with research, do not guess):** number of target firms x annual contract value x attainable share. Start from regulator and industry registries of brokerages, exchanges and payment institutions in one region, then expand.
- **Go-to-market:** design partners through compliance consultants and AML communities; a measured backtest as the sales asset; reference customers before outbound.
- **Land and expand:** triage and SAR drafting first; then case management, screening, and the fraud and churn modules already in the briefs.

---

## 10. Evaluation: Google's eval-flywheel method applied

1. **Datasets from traces and synthetic scenarios.** Every live turn's trace becomes a candidate eval case; generate synthetic user scenarios for coverage.
2. **Two kinds of checks.** Deterministic (the numeric auditor, citation coverage, tool-order and bounded-cycle trajectory checks) and rubric-based LLM-as-judge for narrative quality, with a human-labelled calibration set to keep the judge honest.
3. **Cluster failures**, not just count them; fix the prompt, tool or data cause; re-run and compare before and after.
4. **Gate in CI**: the deterministic suite blocks merges; judge scores are tracked and trended.
5. **Adversarial suites**: prompt injection through tool output and dataset fields, attempts to bypass four-eyes, wrong-figure-near-dates tests for the auditor.
6. **Backtest harness** for M4 on design-partner or public labelled data.

---

## 11. Roadmap with decision gates

No dates; each phase has an exit criterion, and gates can stop work.

| Phase | Work | Exit / gate |
|---|---|---|
| **A. Agent foundation** | ADR superseding 016 and spec 021; ADK supervisor plus the AML specialist at parity with current tests; real routing; replay status in the UI; latency and cost budget measured | Parity green; M5 measured; live turn p95 recorded |
| **B. Walking skeleton** | "Close one alert" end to end on the deployed system: dossier, one geographic lens, SAR draft, dual-approved action, ledger verify, wired shelf | Demo works on the public URL; M1 timed on seeded cases |
| **C. Evidence lenses** | Jurisdiction risk, IP-versus-KYC, corridors, precedent counts, sanctions port; reference data pipeline | Each lens passes the "does it shorten an investigation" test or is cut |
| **D. Proof** | Eval flywheel, backtest harness, adversarial suite, first measured M3 and M4 | `[MEASURED]` results published in the repo |
| **E. Pilot readiness** | SLOs and alerts, cost caps, DR note, security review, design-partner shadow-mode runbook | Gate: do design partners want to proceed (section 6)? |

Critical path: A then B then D. Phase C items are parallelizable and individually cuttable. The v2 scenarios for partner churn and macro shocks are deferred until the wedge is proven.

---

## 12. Risks, decisions and kill criteria

| Risk | Mitigation |
|---|---|
| Crowded category (funded competitors) | Win on measured proof and auditability; do not out-feature on "agents" |
| LLM errors in a regulated workflow | Deterministic auditor, human-owned final decisions, dual control, replay; never claim autonomy |
| Backtest shows low agreement | Treat as the most valuable finding; narrow scope to the alert types where agreement is high |
| Data licences and real-person harm | Section 8 policies; verify GLEIF and any labelled-data licences before ingestion |
| Latency and cost | Budgets, context caching, model routing, correction cap (section 7.4) |
| Platform previews (managed MCP, ADK 2.0 churn, Python 3.14 compatibility) | Wrap behind our own tool port; pin versions; keep parity tests |
| Scope growth | Phase gates; the map and extra scenarios are cuttable by design |

| Decision | Status |
|---|---|
| D-1 No natural persons from leak data | Decided |
| D-2 Graph backend | Gate: only if precomputed tables are too slow; spike BigQuery then Spanner |
| D-3 GLEIF and labelled-data licences | Verify before ingestion |
| D-4 `[EXTERNAL]` provenance tag | ADR |
| D-5 Managed MCP preview status | Wrap behind tool port |
| D-6 Pricing model | Test with design partners |
| D-7 ADK in-process versus separate service | In-process until load requires a split |

---

## 13. Sources
- FinCEN SAR volumes: [Thomson Reuters SARs report 2024](https://www.thomsonreuters.com/en-us/posts/corporates/sars-report-2024) (calendar 2024 original filings), [FinCEN FY2024 infographic](https://www.fincen.gov/sites/default/files/shared/FinCEN-Infographic-Public-2025-508.pdf) (top-10 filer share); fiscal-2024 total from a [secondary summary](https://www.fluxforce.ai/statistics/sar-filing-volumes-by-country), verify against FinCEN.
- False-positive rates and cost of compliance (vendor and industry commentary, secondary): [Lucinity](https://lucinity.com/blog/understanding-false-positives-in-transaction-monitoring-what-causes-them-and-how-can-ai-can-reduce-operational-waste), [Flagright](https://flagright.com/understanding-false-positives-in-transaction-monitoring), [Elliptic](https://www.elliptic.co/corpus/gen-3220/profit-maximization/profit-impact-of-false-positives-in-crypto-aml-and-sanctions-screening.html).
- Competitors and funding (secondary; conflicting round details): [Hawk Series C](https://fintech.global/2025/04/08/hawks-ai-solutions-attract-56m-for-global-aml-efforts/), [AI x Fintech landscape](https://insights.tryspecter.com/ai-x-fintech-landscape/), [AML software roundup](https://salv.com/blog/best-aml-software/).
- Regulatory direction on AI in AML (secondary; verify primary texts): [FinTech Global, readiness 2026](https://fintech.global/2025/11/26/ai-in-aml-readiness-now-key-to-2026-success/), [explainability](https://fintech.global/2026/08/26/explainability-becomes-amls-new-ai-currency/), [auditable AI](https://www.sanctions.io/blog/auditable-ai-in-aml).
- Data and platform: [ICIJ Offshore Leaks](https://offshoreleaks.icij.org), [OpenSanctions licensing](https://www.opensanctions.org/docs/commercial/exemption/), [OpenBB licence FAQ](https://docs.openbb.co/odp/python/faqs/license), [Overture on BigQuery](https://docs.overturemaps.org/getting-data/data-mirrors/bigquery/), [Google MCP supported products](https://docs.cloud.google.com/mcp/supported-products), [ADK 2.0](https://cdn.jsdelivr.net/gh/google/adk-python@main/README.md), [Google agent eval flywheel skill](https://raw.githubusercontent.com/google/skills/main/skills/cloud/agent-platform-eval-flywheel/SKILL.md).
