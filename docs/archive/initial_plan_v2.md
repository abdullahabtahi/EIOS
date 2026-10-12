# Deriv Enterprise Intelligence Operating System (Deriv EIOS)
## Master Architecture & Production Ground Truth Specification — v2 (Red-Team Overhauled)
**v2 Provenance:** This revision incorporates a red-team pass against the actual hackathon master briefing (`docs/enterprise_briefing.md`). See `docs/red_team_findings.md` for the full finding-by-finding rationale and `docs/synthetic_data_strategy.md` for the new Layer 0 design.
**Classification:** Enterprise Production Architecture & Live Hackathon Demonstration Specification  
**Sponsors:** QuantumBlack (McKinsey Rewired 2nd Ed) × Palantir Financial Services FDE × Google Cloud Platform  
**Target Environment:** Deriv Global Broker Ecosystem (Deriv MT5, Deriv Trader, DBot, Deriv P2P, Payment Agents, Synthetics & Forex)  
**Reference Architecture:** [Palantir Financial Services Solutions](https://www.palantir.com/offerings/financial-services/) (Citi Wealth, Global Investment Bank SCV, Risk Attribution & Asset Allocation)  
**Flagship Operational Application:** [Deriv Sentinel: AI-Powered Client Fraud Detection & Investigation](https://drive.google.com/file/d/1IXu23odcPnKlHCKAfSF2qFaoh4Vn9aBw/view) (Slashing 95% False Positives, 5x Investigator Productivity, 30-Second Dossiers, 23-Account Network Revelation)  
**Budget Envelope:** GCP Serverless Tier (Optimized for $100+ Credit Envelope, 100% Scale-to-Zero, ~$12.65/mo)  
**Design System:** QuantumBlack Design System (`mckinsey/quantumblack-design-system` — AI-Native shadcn / Radix / Tailwind)  

---

## 1. Executive Summary & Design Philosophy

### 1.1 The Enterprise Vision: Beyond Point Analytics to Operational Decisions
Deriv operates at institutional scale: **3+ million clients across 190+ countries, processing over $700 billion in monthly trading volume across 168+ million monthly deals**. 

Like the tier-1 global institutions documented in Palantir's Financial Services practice (e.g. Citi Wealth, global investment banks), Deriv's primary bottleneck is **data fragmentation across legal entities, trading platforms, and jurisdictions**:
- Data sits trapped in silos: MetaTrader 5 (MT5) servers, Deriv Trader WebSockets, Deriv P2P (DP2P) escrow databases, regional Payment Agent networks, and KYC document stores.
- Traditional BI dashboards and static reporting are **shelfware**—they show lagging historical metrics but cannot execute real-time operational decisions or coordinate cross-domain workflows.

The **Deriv Enterprise Intelligence Operating System (EIOS)** solves this by deploying a **Kinetic Enterprise Ontology** that serves as an operational digital twin for the entire brokerage.

### 1.2 The Relationship Between the OS and the Three Operational Flagship Modules
To maintain absolute architectural clarity and fulfill the complete trio of official Deriv Challenge Briefings:
- **The Master Deliverable is the Enterprise Intelligence Operating System (Deriv EIOS):** A decoupled, multi-domain data and reasoning fabric unifying all 6 broker business functions (*Client, Financial, Partner, Operational, Competitive, and Compliance/Risk*).
- **The Platform Operates Three Interconnected Flagship Operational Modules:**
  1. **Module A — Client Fraud Sentinel ([Briefing 1](https://drive.google.com/file/d/1IXu23odcPnKlHCKAfSF2qFaoh4Vn9aBw/view)):** Tackles client multi-accounting, deposit-to-income spikes, 95% false-positive reduction, 30-second AI dossiers, 23-account syndicate ring revelation, and 1-click audit-ready regulatory SAR generation.
  2. **Module B — Partner Fraud & Opposite Trading Sentinel ([Briefing 2](https://drive.google.com/file/d/1fHkbEBAgcGb8nieJM3S36lc-7RRxCUsp/view)):** Targets relational partner abuse, opposite trading schemes across affiliate pairs, mirror trading in lockstep, bonus abuse (deposit/1 micro-trade/withdraw), sub-affiliate (SO) multi-tier gaming, and 7-partner/23-sub-affiliate/184-client syndicate ring mapping with commission clawback.
  3. **Module C — Partner Churn Radar & Retention Engine ([Briefing 3](https://drive.google.com/file/d/1Sf6XlxEit4Mrf974Yy4QbH5mMtz8LMnF/view)):** Solves silent partner disengagement through multi-signal early warning (login decay, referral volume decay, ticket sentiment, competitor poaching like Exness/XM), cohort risk detection, and proactive retention playbooks during the optimal intervention window.

### 1.3 The Fourth Capability: Executive Synthesis & Cross-Domain Causal Narrative (Not a Module — the Platform's Core Promise)
Per `docs/red_team_findings.md` Finding 1, the master hackathon briefing (`docs/enterprise_briefing.md`) states its single highest bar twice, and it spans **four domains in one causal chain** — Competitive → Partner → Client → Financial — e.g. *"Client LTV is declining because partner mix shifted toward lower-quality channels, which happened because our commission structure became uncompetitive after competitor X raised partner payouts."* No single flagship module produces this: Module A reasons within Client+Compliance, Module B within Partner+Client, Module C within Partner+Competitive. None of them ever touches Financial P&L or chains more than two domains together.

The EIOS therefore hosts a **fourth capability that is not a module but the platform's organizing promise**: the **Executive Synthesis Engine**, detailed in new §5.4. It sits above Modules A/B/C, consumes their outputs plus the raw Financial and Competitive Intelligence data products the modules don't otherwise touch, and composes genuine 4-domain causal narratives, scenario simulations ("if competitor X acquires competitor Y..."), and a proactive "Good morning" executive briefing — the three "blow our minds" bullets v1 otherwise left unaddressed.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                   DERIV ENTERPRISE INTELLIGENCE OPERATING SYSTEM (DERIV EIOS)                         │
│                   The Decoupled, Kinetic Digital Operating System for the Entire Broker                │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  DOMAIN 1: CLIENT INTELLIGENCE (Global Customer Master, Onboarding Velocity, Churn, LTV, Next Best)   │
│  DOMAIN 2: FINANCIAL INTELLIGENCE (Dealer B-Book Yield, A-Book LP Hedging, Cash Flow Variance)         │
│  DOMAIN 3: PARTNER INTELLIGENCE (Affiliate RevShare 30-45%, IB Daily Lot Economics, PA Cashier Flow)   │
│  DOMAIN 4: OPERATIONAL INTELLIGENCE (MT5 Latency, WebSocket ws.derivws Ticks, DP2P Escrow Settlement) │
│  DOMAIN 5: COMPETITIVE INTELLIGENCE (Exness/XM Spread Benchmarking, Overnight Swap Arbitrage)          │
│  DOMAIN 6: COMPLIANCE & RISK (Multi-Jurisdiction Governance: MFSA, LFSA, VFSC)                        │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                 THE THREE OPERATIONAL FLAGSHIP MODULES                                 │
│                                                                                                        │
│  ┌───────────────────────────────┐ ┌───────────────────────────────┐ ┌───────────────────────────────┐ │
│  │ MODULE A: CLIENT SENTINEL     │ │ MODULE B: PARTNER INTEGRITY   │ │ MODULE C: PARTNER RADAR       │ │
│  │ (Briefing 1: Client Fraud)    │ │ (Briefing 2: Partner Fraud)   │ │ (Briefing 3: Partner Churn)   │ │
│  │ • 95% False-Positive Gate     │ │ • Opposite Trading Schemes    │ │ • Silent Disengagement Early  │ │
│  │ • 30-Sec Investigation Dossier│ │ • Mirror Trading in Lockstep  │ │   Warning (Login/Volume Decay)│ │
│  │ • 23-Account Client Syndicate │ │ • Multi-Tier Sub-Affiliate    │ │ • Multi-Signal Risk Scoring   │ │
│  │ • 1-Click MFSA/LFSA SAR Gen   │ │   Gaming (7 Ptrs / 184 Accts) │ │ • Competitor Poaching Alert   │ │
│  │ • Two-Phase Commit [Freeze]   │ │ • Commission Clawback Token   │ │ • Proactive Retention Playbook│ │
│  └───────────────────────────────┘ └───────────────────────────────┘ └───────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Institutional Financial Services Insights (Palantir & McKinsey / QuantumBlack)

From our empirical analysis of tier-1 institutional deployments across **Palantir Financial Services** ([`palantir.com/offerings/financial-services/`](https://www.palantir.com/offerings/financial-services/)) and **McKinsey Financial Services & QuantumBlack** ([`mckinsey.com/industries/financial-services/our-insights`](https://www.mckinsey.com/industries/financial-services/our-insights)), we integrate eight battle-tested architectural pillars:

### 2.1 Palantir Financial Services Pillars
#### Pillar 1: Global Federated Customer Master (GFCM) & Single Client View (SCV)
- **Palantir Precedent (Citi Wealth & Global Investment Bank):** Citi Wealth built a Global Federated Customer Master with Palantir, **reducing account opening from 9 days to seconds, and cutting required personnel from 50 people to 1**. A global investment bank resolved **4 billion records into a Single Client View**, speeding up client searches by **90%** and investigation reviews by **80%**.
- **Deriv Application:** We implement a unified entity resolution engine that connects a trader’s identity across all platforms: **Deriv Trader, Deriv MT5, Deriv X, DBot, Deriv GO, and DP2P Cashier**. Regardless of whether a client deposits via crypto or local payment agents, the EIOS resolves their activity into an authoritative Single Client View.

#### Pillar 2: Risk Attribution & Real-Time Position Calibration
- **Palantir Precedent (Asset Management & Markets):** Palantir continuously calibrates fund positions against internal risk models and external market data, adjusting exposures flexibly and flagging compliance deviations in a single unified workflow.
- **Deriv Application:** Deriv's unique profit engine is its proprietary **Derived (Synthetic) Indices (Volatility, Boom/Crash, Step)**, which run on pure dealer **B-Book execution** (100% internalized spread capture). The EIOS provides real-time **Dealer Book Yield vs. A-Book Hedging Exposure** monitoring, instantly alerting when client directional exposure on Volatility 75 breaches capital risk buffers.

#### Pillar 3: Next Best Action & Behavioral Cohorting
- **Palantir Precedent (Global Commercial Bank):** Palantir powers Next Best Offer (NBO) marketing by integrating customer, transaction, and behavioral interactions, deploying new models in **hours instead of 6 months** and boosting net response rates by **15%**.
- **Deriv Application:** Real-time behavioral clustering identifies trader fatigue, drawdown churn hazard on Boom 1000, and VIP upgrade eligibility, generating automated interventions to preserve client lifetime value.

#### Pillar 4: Multi-Jurisdiction Governance by Design
- **Palantir Precedent (Enterprise Digitization across Jurisdictions):** Supporting 15,000+ users across legal entities with granular security markings and role-based access.
- **Deriv Application:** Deriv operates across conflicting regulatory regimes: **Malta MFSA (ESMA 1:30 leverage ceiling, negative balance protection)** vs. **Labuan LFSA, Vanuatu VFSC, and BVI FSC (offshore 1:1000 leverage)**. The EIOS enforces mathematical jurisdictional boundaries, ensuring European clients cannot be routed into offshore leverage buckets.

### 2.2 McKinsey & QuantumBlack Financial Services Pillars
#### Pillar 5: Network Science to Defeat the 98% False-Positive Barrier
- **McKinsey Precedent (*Network Analytics in AML*):** Traditional rules-based customer risk rating and transaction monitoring exhibit **false-positive rates of over 98%**, blinding institutions to syndicates. McKinsey proves that overcoming this requires **Network Analytics & Community Detection**—analyzing subcomponents of connected graphs to find shared devices, accounts, and payment links rather than isolated individual transactions.
- **Deriv Application:** In **Deriv Sentinel**, the graph engine analyzes subcomponents of the customer network. When an account exhibits high deposit velocity, the system traverses the graph to uncover if it coordinates with a **23-account syndicate sharing WebGL device hashes and Payment Agent conduits**.

#### Pillar 6: QuantumBlack Integrated Fraud Strategy (Ending the "Balloon Squeeze")
- **QuantumBlack Precedent (*UK Bank Fraud Transformation*):** QuantumBlack helped a leading UK bank **recover 95% of estimated fraud financial losses** and accurately identify **86% of fraud incidences** by integrating cross-channel payment telemetry with historical fraud typologies. Crucially, QuantumBlack emphasizes eliminating the "squeezing a balloon" effect (where fraud blocked on credit cards simply migrates to P2P or mobile).
- **Deriv Application:** Deriv EIOS monitors fraud vectors uniformly across **MetaTrader 5 CFDs, Deriv Trader Synthetics, Deriv P2P (DP2P), and local Payment Agents**, ensuring fraud cannot migrate across cashier channels while maintaining low onboarding friction.

#### Pillar 7: Capital Markets Architecture Renewal & Capital Optimization
- **McKinsey Precedent (*Foundation for Value in Capital Markets*):** In capital markets, a superior data and application architecture cuts **Risk-Weighted Assets (RWA)** and saves tier-1 institutions up to **$300 million annually in capital exposures** by avoiding overly conservative risk assumptions and mismatches in trade booking, while boosting front-office producer efficiency by up to **8x**.
- **Deriv Application:** In the **Financial & Operational Intelligence domains**, the EIOS continuously tracks Deriv’s **Net Dealer Book Capital at Risk** across its proprietary Derived Indices (Volatility 100, Boom 1000). Sub-second tick aggregation prevents risk warehousing over-exposure, safeguarding broker clearing margins.

#### Pillar 8: GenAI as the "Virtual Risk Expert"
- **McKinsey Precedent (*GenAI in Corporate & Investment Banking*):** GenAI delivers maximum enterprise value not as an autonomous chatbot, but as an embedded **"Virtual Risk Expert"**—reading dense regulatory filings, synthesizing customer background dossiers, identifying relevant compliance requirements, and drafting audit-ready documentation for senior human officers.
- **Deriv Application:** The **30-Second Investigation Copilot** in Deriv Sentinel operationalizes this exact paradigm: ingesting cross-system telemetry to auto-draft an audit-ready **Suspicious Activity Report (SAR)** formatted for **Malta MFSA (ESMA rules)** and **Labuan LFSA**, ready for human sign-off in 1 click.

---

## 3. End-to-End System Topology

**Layer/Tier reconciliation note:** `.agents/skills/mckinsey-rewired-2nd/SKILL.md` frames the same system as a 4-Tier architecture. The mapping is: Layers 1–2 below ≈ Tier 1–2A/2B, Layer 3 ≈ Tier 3, Layers 4–5 ≈ Tier 4A/4B. No functional conflict — the skill just merges what this document splits into Layers 4/5 into a single cockpit+write-back tier.

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 0. SYNTHETIC ENTERPRISE DATA FOUNDRY (Layer 0 — see docs/synthetic_data_strategy.md)              │
│    • Seeded, reproducible per-domain generators (gen_client/partner/financial/competitive/ops.py) │
│    • Produces every demo dataset with target fraud/churn/causal patterns embedded by construction │
│    • Writes into the SAME Pub/Sub topics / GCS landing zone a real MT5/CRM feed would use          │
│    • Palantir precedent: Foundry Pilot — isolated seed-data container, agents never touch prod    │
└─────────────────────────────────┬─────────────────────────────────────────────────────────────────┘
                                  │ (synthetic events, indistinguishable downstream from real ones)
                                  ▼
[ MT5 Execution Engine / Deriv Trader WebSockets / DP2P Escrow / Payment Agents / KYC Vaults ]
                                              │
                        (Real-Time Webhook / Pub/Sub Event Push)
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. MULTIMODAL INGESTION & DATA CONTRACT SPINE (GCP Serverless)                                   │
│    • Cloud Pub/Sub: Ingests trade execution ticks, DP2P disputes, auth logs, deposit events       │
│    • Cloud Run Streaming Worker (FastAPI + DuckDB streaming buffer): Sliding micro-batches        │
│    • Data Product Contracts: Pydantic circuit breaker (<0.05% schema/null drift halts bad feeds)  │
│    • Raw Storage: BigQuery Ingestion Buffer + Cloud Storage (Parquet Lakehouse)                   │
└─────────────────────────────────┬─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. KINETIC ENTERPRISE ONTOLOGY & SEMANTIC METRIC ENGINE (Palantir Foundry × McKinsey Rewired)     │
│    ┌───────────────────────────────────────┐ ┌───────────────────────────────────────────────────┐ │
│    │ QUANTITATIVE METRIC LAYER (Tier 2A)   │ │ TOPOLOGICAL PROPERTY GRAPH (Tier 2B)              │ │
│    │ • Cube Core Semantic Layer (cube.dev) │ │ • NetworkX In-Memory Property Graph               │ │
│    │ • Governed KPI Formulas & Measures    │ │ • ClientAccount, Device, IP, PaymentMethod Nodes  │ │
│    │ • DuckDB Columnar Vectorized OLAP     │ │ • Louvain Community & 23-Account Ring Detection   │ │
│    │ • Pre-calculated Rolling Window State │ │ • Active Relationships: [:OPERATED_FROM], [:TRADES]│
│    └──────────────────────┬────────────────┘ └─────────────────────────┬─────────────────────────┘ │
│                           │                                            │                           │
│                           └──────────────────────┬─────────────────────┘                           │
│                                                  ▼                                                 │
│                           ┌───────────────────────────────────────────────┐                        │
│                           │ ONTOLOGY API (Objects + Function-Backed Props)│                        │
│                           │ • Dynamically computes live object state      │                        │
│                           │ • Exposes registered Action Types & Criteria  │                        │
│                           │ • NOTE: per Foundry doctrine, "the Ontology   │                        │
│                           │   is not a semantic layer" — it is the four-  │                        │
│                           │   fold union of Data (this layer) + Logic     │                        │
│                           │   (Function-Backed Props) + Action (Layer 5   │                        │
│                           │   Action Types) + Security (Layer 3 RBAC/     │                        │
│                           │   Markings). See docs/foundry.md.             │                        │
│                           └──────────────────────┬────────────────────────┘                        │
└──────────────────────────────────────────────────┼─────────────────────────────────────────────────┘
                                                   │
                                                   ▼ (Strict OMCP Interface + Deriv Agent Auth Hub)
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. ENTERPRISE REASONING & MULTI-AGENT COPILOT MESH (LangGraph on Cloud Run)                       │
│    • Supervisory Router (Vertex AI Gemini 3.8 Flash via google-genai SDK): Intent, RBAC, Plan     │
│    • Deriv Agent Auth Hub Security: X-Human-Context OIDC validation against Cloud SQL RBAC         │
│    • Amy Prompt-Caching Prefix: Deterministic prefix cuts token cost 77% (85.8% cache-hit rate)   │
│    • Specialized Domain Agents:                                                                   │
│      - Client Intelligence Agent (Customer 360, Churn, Next Best Action)                          │
│      - Financial & Dealer Book Agent (B-Book Synthetics Yield, A-Book LP Slippage, Hedging Delta)  │
│      - Partner Intelligence Agent (Affiliate RevShare Leakage, IB Daily Lots, PA Cashier Flow)    │
│      - Operational Health Agent (MT5 Gateway Latency, WebSocket Ticks, DP2P Escrow Times)          │
│      - Sentinel Fraud & AML Copilot (30-Sec Dossiers, 23-Account Ring Revelation, SAR Generation) │
│      - Executive Synthesis Agent (4-Domain Causal Narrative Composition — see §5.4)               │
│      - Scenario Simulation Engine (DoWhy shock-injection: "if competitor X acquires Y...")         │
│      - Morning Briefing Generator (Scheduled Cloud Workflows job; proactive, unprompted synthesis) │
│    • Pearlian Causal Engine (DoWhy): Evaluates interventions E[Y|do(X=x)] + Refutation Tests       │
│    • Metric Auditor Gate: Intercepts & asserts 100% faithfulness between model text and metrics    │
└─────────────────────────────────┬─────────────────────────────────┬───────────────────────────────┘
                                  │                                 │
           (SSE Event Streams &   │                                 │ (HMAC-SHA256
            Causal Lineage Diffs) │                                 │  Action Intent Token)
                                  ▼                                 ▼
┌──────────────────────────────────────────────────┐ ┌──────────────────────────────────────────────┐
│ 4. COMMON OPERATIONAL PICTURE (COP) COCKPIT      │ │ 5. GOVERNED ACTION TYPES & DECISION LEDGER   │
│    • Next.js 15 (React 19, Cloud Run)            │ │ • Cloud Workflows (Serverless Orchestration) │
│    • QuantumBlack Design System (QBDS AI-Native) │ │ • Human-on-the-Loop Governed Action Bar:     │
│    • Strawberry GraphQL + SSE Streaming          │ │   - [ Freeze Account / Payment Rail ]        │
│    • Multi-Domain Executive Dashboard:           │ │   - [ Adjust Affiliate Commission Tier ]     │
│      - Domain Selector: Client, Finance, Fraud   │ │   - [ Reroute MT5 Execution Gateway ]        │
│      - 30-Second Fraud Dossier & Case Timeline   │ │   - [ Export Audit-Ready Regulatory SAR ]    │
│      - Interactive React Flow Ring Graph (23 Accts)│ • BigQuery 30-Day Decision Attribution Ledger│
│    • What-If Counterfactual Branch Slider        │ │ • Closed-Loop Continuous Learning Flywheel:  │
│                                                   │ │   decision_outcomes_ledger (BigQuery) w/     │
│                                                   │ │   30/60/90-day predicted-vs-actual columns + │
│                                                   │ │   causal-DAG edge-weight recalibration rule  │
│                                                   │ │   (see mckinsey-rewired-2nd/references/      │
│                                                   │ │   decision-learning-flywheel.md)             │
└──────────────────────────────────────────────────┘ └──────────────────────────────────────────────┘
```

---

### 3.1 Exhaustive Technology Stack, Frameworks & Libraries Specification

To deliver an enterprise-grade system matching Palantir Foundry/AIP and McKinsey/QuantumBlack *Rewired (2nd Edition)* quality standards within the GCP $100 budget envelope, the platform employs a battle-tested, modern, and strictly open-source technology stack:

| Layer / Subsystem | Technology / Library | Version | Architectural Role & Justification |
|---|---|---|---|
| **Foundation Models (AI)** | **`google-genai`** SDK | `>=1.33.0` | Official unified Google Gen AI SDK (`genai.Client(vertexai=True, ...)`). Unifies Developer API and Vertex AI Enterprise mode. |
| | **`gemini-3.8-flash`** | Latest GA | **Unified Operational & Forensic Engine**. Sub-second latency, 1M+ token context window, native Pydantic JSON schema generation (`response_schema`), native tool-calling, and prefix prompt-caching (Amy pattern). Single model powering routing, 30-sec dossiers, and SAR legal generation. |
| **Agent Mesh & Orchestration** | **`langgraph`** | `>=0.2.74` | Stateful multi-agent DAG execution, cyclical tool loops, conditional branching, state persistence (`MemorySaver`), and human-in-the-loop interruption (`interrupt()`). |
| | **`langchain-core`** | `>=0.3.0` | Base message abstractions (`HumanMessage`, `AIMessage`, `ToolMessage`), prompt templates, and standardized tool definitions. |
| **Semantic Metric Layer (Tier 2A)** | **`Cube Core`** (`cube.dev`) | `>=0.35.0` | **Universal Headless Semantic Metric Layer (McKinsey Rewired Pattern 1)**. Defines declarative data models (YAML/JS), standardized KPI formulas, and pre-aggregations. Guaranteed zero-hallucination quantitative metrics for agents and dashboards. Exposes SQL, REST, and GraphQL metric APIs. |
| **Causal Inference & Verification** | **`dowhy`** | `>=0.11.0` | **Pearlian Causal DAG Engine**. Models interventions ($\mathbb{E}[Y \mid do(X = x)]$), backdoor/frontdoor adjustment, and statistical refutations (Placebo, Random Common Cause). |
| | **`scipy` / `numpy` / `statsmodels`** | `>=1.14 / >=2.1 / >=0.14` | Statistical significance testing, distribution fitting (KS-test for deposit anomalies), and z-score baseline calibrations. |
| **Kinetic Ontology & Data Product Engine** | **`duckdb`** | `>=1.1.0` | **In-Process Vectorized Columnar OLAP Engine**. Embeds directly in Cloud Run container; executes sub-millisecond queries with zero idle cost. Serves as execution engine for Cube Core and dynamic Function-Backed Columns. |
| | **`pyarrow`** | `>=17.0.0` | Zero-copy columnar memory buffers between DuckDB and Python analytical processes. |
| | **`pydantic`** | `>=2.8.0` | Enterprise Kinetic Ontology object definitions, runtime type validation, serialization, and JSON schema compilation for LLM tool binding. |
| | **`networkx`** | `>=3.3.0` | **Topological Graph Engine**. Sub-10ms graph traversals, Louvain community detection, cycle detection, and bipartite syndicate matching (23-account rings). |
| | **`sqlalchemy` / `aiosqlite`** | `>=2.0.0` | Asynchronous metadata catalog, ontology registry, and local transaction tracking. |
| **Synthetic Data & Seeding (Layer 0)** | **`numpy` / `faker`** | `>=2.1 / >=28.0` | Powers the per-domain seeded generators in `docs/synthetic_data_strategy.md` (`gen_client.py`, `gen_partner.py`, etc.) — reproducible distributions, realistic names/devices, and pattern-first scenario construction validated against the same `pydantic` contracts used by real ingestion. |
| **Backend API & Query Protocols** | **`fastapi`** | `>=0.115.0` | **Core Asynchronous Application Gateway & Service Host**. Hosts ASGI runtime, OMCP tool execution endpoints (`/api/v1/omcp`), SSE streams, and Two-Phase Commit actions. |
| | **`strawberry-graphql`** | `>=0.282.0` | **Strongly-Typed Kinetic Ontology Graph Router**. Mounted inside FastAPI at `/graphql`. Exposes multi-hop entity property graph directly to Next.js and React Flow without N+1 query overhead. |
| | **`uvicorn[standard]`** | `>=0.30.0` | High-throughput ASGI web server with `uvloop` and `httptools`. |
| | **`sse-starlette`** | `>=2.1.0` | Server-Sent Events (SSE) streaming engine for real-time agent thought streaming and live case dossier generation at `/api/v1/stream`. |
| **Security & Identity (Deriv Agent Auth Hub)** | **`google-auth`** | `>=2.34.0` | GCP Workload Identity Federation credentials management. |
| | **`pyjwt[crypto]`** | `>=2.9.0` | Cryptographic decoding and verification of OIDC JWT tokens (`X-Human-Context`) enforcing Dynamic RBAC. |
| | **`cryptography`** | `>=43.0.0` | HMAC-SHA256 signature generation and verification for Two-Phase Commit Action Intent Tokens. |
| **GCP Cloud Services & Storage** | **`google-cloud-bigquery`** | `>=3.25.0` | Append-only 30-day decision attribution ledger, audit trail, and counterfactual feedback storage (On-Demand pricing). |
| | **`google-cloud-storage`** | `>=2.18.0` | Parquet lakehouse cold storage for historical transactional partitions. |
| | **`google-cloud-pubsub`** | `>=2.24.0` | Asynchronous event bus for real-time trade/deposit event ingestion. |
| | **`google-cloud-secret-manager`** | `>=2.20.0` | Zero-plaintext runtime retrieval of API keys, HMAC secrets, and service credentials. |
| **Frontend Framework & Runtime** | **`next` (Next.js 15)** | `15.0.x` | Modern App Router, Server Actions, React Server Components (RSC), and Turbopack bundler. |
| | **`react` / `react-dom`** | `19.0.x` | Latest React core with enhanced concurrent rendering, optimistic UI transitions, and `useActionState`. |
| **Design System & Styling (QBDS)** | **`@mckinsey/quantumblack-design-system`** | Latest | McKinsey QuantumBlack Design System tokens, typography, and AI-native visual aesthetics. |
| | **`@radix-ui/react-*`** | Latest | Accessible unstyled headless UI primitives (Dialog, DropdownMenu, Tabs, Tooltip, Popover, Slider, Accordion). |
| | **`tailwindcss`** | `>=3.4.0` | Utility-first CSS framework configured with QuantumBlack Midnight palette (`#0B0F19`, `#00E5FF`, `#FF1744`, `#00E676`). |
| | **`class-variance-authority` (`cva`)** | `>=0.7.0` | Type-safe component variant orchestrator for design system components. |
| | **`lucide-react`** | `>=0.450.0` | Cohesive enterprise UI iconography. |
| **Interactive Visualization & Graph** | **`@xyflow/react` (React Flow v12)** | `>=12.3.0` | High-performance interactive node-edge graph canvas for 23-account syndicate ring visualization with custom interactive cards. |
| | **`@elkjs/elkjs` / `dagre`** | Latest | Automated hierarchical and force-directed graph layout calculation. |
| | **`recharts`** | `>=2.12.0` | Financial telemetry, income-to-deposit ratio curves, and transaction velocity histograms. |
| **State Management & Data Fetching** | **`zustand`** | `>=4.5.0` | Lightweight global client state for live case triage, active action proposals, and timeline scrubbing. |
| | **`@tanstack/react-query`** | `>=5.50.0` | Robust async server-state caching, background revalidation, and SSE stream integration. |
| **Development & Build Tooling** | **`uv`** | Latest | Ultra-fast Python package resolver and virtual environment manager (10-100x faster than pip). |
| | **`pnpm`** | Latest | Fast, disk-space efficient package manager for Node.js. |
| | **`typescript`** | `>=5.6.0` | Strict end-to-end type safety for frontend components and API contracts. |

---

## 4. The 6 Business Domains of Deriv EIOS

```
                                      DERIV OPERATIONAL ONTOLOGY
                                                  │
    ┌────────────────┬────────────────┬───────────┼───────────┬────────────────┬────────────────┐
    ▼                ▼                ▼           ▼           ▼                ▼                ▼
┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 1. CLIENT INTEL │ │ 2. FINANCIAL    │ │ 3. PARTNER INTEL │ │ 4. OPERATIONAL  │ │ 5. COMPETITIVE  │ │ 6. RISK & COMPL │
│ • Customer 360  │ │ • Dealer B-Book │ │ • RevShare 30-45%│ │ • MT5 Latency   │ │ • Exness/XM     │ │ • MFSA vs VFSC  │
│ • Onboard Speed │ │ • LP A-Book Cost│ │ • IB Daily Lots  │ │ • wss.derivws ms│ │   Spread Bench  │ │ • DP2P AML Flow │
│ • Churn Hazard  │ │ • Margin Yield  │ │ • PA Cashier Bal │ │ • DP2P Escrow ms│ │ • M&A/News Feed │ │ • [SENTINEL]   │
└─────────────────┘ └─────────────────┘ └──────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
```

**Note on Domain 5 fidelity:** the original 5-box rendering of this diagram omitted Competitive Intelligence entirely — an internal inconsistency versus the 6-domain claim in §1.2/§2. It is restored above as its own box and, per `docs/red_team_findings.md` Finding 1/2, needs a materially richer synthetic feed than the other domains (competitor pricing-change events, M&A rumor events — see `gen_competitive.py` in `docs/synthetic_data_strategy.md`) because it is a required input to both Scenario Simulation and the cross-domain Executive Synthesis narrative (§5.4), not just to Module C's poaching NLP.

### Domain 1: Client Intelligence (Customer 360 & Onboarding Velocity)
- **Inspired by:** Citi Wealth Global Federated Customer Master.
- **Key Entities:** `ClientAccount`, `TradingProfile`, `OnboardingFunnel`.
- **Function-Backed Metrics:** `onboarding_cycle_time_sec`, `churn_hazard_score`, `next_best_action_propensity`.
- **Causal Question:** *Why did 30-day VIP retention in Nigeria drop 14% after the minimum deposit rule change?*

### Domain 2: Financial Intelligence (Dealer Book Yield & Asset Allocation)
- **Inspired by:** Palantir Portfolio 360 & Risk Attribution.
- **Key Entities:** `DealerBookPnL`, `LiquidityProviderExposure`, `NetClearingMargin`.
- **Function-Backed Metrics:** `synthetics_b_book_yield`, `lp_hedging_slippage_cost`, `net_capital_at_risk`.
- **Causal Question:** *How did spread widening on Volatility 100 affect net broker margin versus client turnover?*

### Domain 3: Partner Intelligence (Affiliate & IB Economics, Partner Fraud & Churn)
- **Inspired by:** Palantir Private Equity Portfolio Monitoring & McKinsey Partner Growth Networks.
- **Directly Operationalized By:** **Module B (Partner Fraud Sentinel)** and **Module C (Partner Churn Radar)**.
- **Key Entities:** `AffiliatePartner`, `SubAffiliate`, `IntroducingBroker` (IB), `PaymentAgent` (PA), `AffiliateClickLog`, `CommissionPayoutLedger`.
- **Function-Backed Metrics:** 
  - `effective_margin_leakage` ($\text{RevShare Paid} - \text{Referred Client Net P&L}$)
  - `opposite_trading_correlation_score` (Pearson correlation of opposite positions across partner pairs)
  - `sub_affiliate_attribution_depth` (N-tier hierarchical tree depth)
  - `partner_disengagement_velocity` (WoW drop in dashboard logins and referral conversions)
  - `churn_hazard_probability` (Multi-signal decay score combining activity, ticket sentiment, and competitor mentions)
- **Causal Questions:** 
  - *Are Partner A and Partner B coordinating referred clients to execute synthetic opposite trading on Boom/Crash to farm RevShare payouts?*
  - *Did the recent payment fee adjustment cause the silent disengagement of our top 5% Southeast Asia master affiliates toward Exness?*

### Domain 4: Operational Intelligence (Trading Infrastructure Assurance)
- **Inspired by:** Palantir Foundry Operational Automation.
- **Key Entities:** `ExecutionGateway` (MT5, Deriv X), `WebSocketEndpoint` (`ws.derivws.com`), `DP2PEscrow`.
- **Function-Backed Metrics:** `mt5_fill_latency_ms`, `synthetic_tick_lag_ms`, `dp2p_dispute_resolution_hours`.
- **Causal Question:** *Did the 45ms latency spike on London MT5 Gateway 2 cause the surge in rejected limit orders?*

### Domain 5: Competitive Intelligence (Market Pricing & Swap Arbitrage)
- **Inspired by:** Palantir Market Intelligence.
- **Key Entities:** `CompetitorBenchmark` (Exness, XM, IC Markets), `SpreadMatrix`.
- **Function-Backed Metrics:** `spread_differential_pips`, `overnight_swap_variance`, `volume_elasticity`.
- **Causal Question:** *What is client trading volume elasticity when Exness cuts EUR/USD spreads by 0.2 pips?*
- **Synthetic feed requirement (per `docs/red_team_findings.md` Finding 1/2):** this domain needs a materially richer feed than a static spread matrix — timestamped competitor pricing-change events and M&A rumor events (`gen_competitive.py` in `docs/synthetic_data_strategy.md`) — because it is a required input to both the Scenario Simulation Engine and the Executive Synthesis Engine's cross-domain narrative (§5.4), not just to Module C's competitor-poaching NLP.

### Domain 6: Compliance & Risk (FEATURING: The Deriv Sentinel Suite)
- **Inspired by:** Palantir Single Client View (SCV) & Global Compliance.
- **Key Entities:** `RegulatoryJurisdiction` (MFSA, VFSC, LFSA), `DeviceFingerprint`, `FraudRingCluster`, `AMLAlert`, `OppositeTradingCluster`.
- **Flagship Applications:** **Module A (Client Fraud Sentinel)** & **Module B (Partner Fraud Sentinel)** (detailed below in §5).

---

## 5. Flagship Operational Feature Suite: The Three Operational Modules

The Deriv EIOS hosts three integrated operational applications directly resolving the complete suite of official hackathon challenge briefings:
1. **Module A — Client Fraud Sentinel** ([Briefing 1](https://drive.google.com/file/d/1IXu23odcPnKlHCKAfSF2qFaoh4Vn9aBw/view)): Client multi-accounting, deposit bursts, 23-account syndicate rings, and regulatory SARs.
2. **Module B — Partner & Affiliate Fraud Sentinel** ([Briefing 2](https://drive.google.com/file/d/1fHkbEBAgcGb8nieJM3S36lc-7RRxCUsp/view)): Opposite trading, mirror trading, bonus harvesting, and multi-tier sub-affiliate syndicate rings with commission clawback.
3. **Module C — Partner Churn Radar** ([Briefing 3](https://drive.google.com/file/d/1Sf6XlxEit4Mrf974Yy4QbH5mMtz8LMnF/view)): Silent disengagement early warning, multi-signal churn scoring, competitor poaching alerts, and proactive retention playbooks.

---

### 5.1 Module A: Client Fraud Detection & Investigation (Briefing 1)

> **⚠️ Ground-truth caveat (per `docs/red_team_findings.md` Finding 6):** Briefing 1 is a Google-Drive PDF this reviewer could not access (sign-in required), and no local transcript (`b1_full.txt`) exists in this repository, unlike Modules B and C which are each backed by a captured `scratch/briefings/b{2,3}_full.txt`. Every specific figure below (95% false-positive reduction, `<450ms` synthesis, the 23-account/3-device/1-PA ring shape) is therefore **unverified against a local source** and may be inherited from general Palantir/AML pattern-matching conventions rather than the actual Briefing 1 requirements. Before this module is decomposed into spec-kit tasks, obtain and capture the real Briefing 1 text the same way `b2_full.txt`/`b3_full.txt` were captured, and re-validate the scope below against it.

```
Incoming Alert: Account #CR84920 flagged with raw risk score 89
                                      │
                                      ▼
                        [Supervisory Router Agent]
                                      │ (Verifies X-Human-Context: <Investigator_OIDC>)
                                      ▼
                        [Amy Prompt-Caching Engine]
      ┌───────────────────────────────────────────────────────────────┐
      │ Immutable Prefix (Cached at 85.8% hit rate):                 │
      │ • Deriv Compliance Rules (MFSA ESMA 1:30 vs VFSC 1:1000)      │
      │ • Fraud Ontology GQL Schema & Function Definitions            │
      │ • OMCP Tool Specs (Search, Traverse, Execute, Propose)        │
      └───────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
                      [Ontology MCP Tool Invocations]
          1. omcp_search_objects(type="ClientAccount", id="CR84920")
          2. omcp_execute_function("income_to_deposit_ratio", id="CR84920") -> 1600%
          3. omcp_traverse_links(source_id="CR84920", link_type="OPERATED_FROM_DEVICE")
             -> Returns DeviceHash #D9921 (Shared by 7 other accounts!)
                                      │
                                      ▼
                    [Predictive False-Positive Filter]
          • Asserts: Is this a legitimate High-Net-Worth trader with verified wealth?
          • Verdict: FALSE (No wealth docs, rapid DP2P smurfing, 3 dispute flags)
                                      │
                                      ▼
                    [Pearlian Causal DAG Evaluator]
          • SCM: [Declared Income] -> [Deposit Explosion] -> [Money Laundering Probability]
          • Intervention: E[Laundering | do(Income = Real)] => Confounder excluded
          • Refutation Test: Placebo Treatment Test passes (p > 0.05 => Causal link verified)
                                      │
                                      ▼
                    [30-Second Copilot Synthesis]
          • Generates 4-part Case Dossier (Risk Score, Root Causes, Timeline, Suggestions)
                                      │
                                      ▼
                      [Metric Auditor Verification Gate]
          • Confirms generated "$8,000 vs $500" claims match DuckDB scalar metrics exactly.
                                      │
                                      ▼
                      Pushed via SSE to Executive Cockpit
```

#### Core Capabilities Realized in Module A:
1. **Intelligent Detection & Pattern Discovery:** Multi-signal detection across KYC documents, MT5 execution ticks, DP2P escrow records, and WebGL device hashes.
2. **Predictive False-Positive Gate:** Slashing 95% false alarms; legitimate VIP traders traveling abroad are auto-dismissed with green audit badges.
3. **30-Second AI Copilot:** Synthesizes fragmented cross-platform data into a 4-part dossier in **<450ms**, complete with chronological event reconstruction.
4. **23-Account Syndicate Revelation:** In-memory graph traversal uncovers hidden rings connecting **Account #CR84920 to 22 other accounts sharing 3 WebGL device hashes and 1 Payment Agent**.
5. **1-Click Regulatory SAR Generation:** Exports an audit-ready Suspicious Activity Report adhering to Malta MFSA & Labuan LFSA specifications.

---

### 5.2 Module B: Partner & Affiliate Fraud Detection (Briefing 2)

Partner fraud is distinct from client fraud: it exploits business relationships, referral structures, and multi-tier commissions rather than stolen cards.

```
Incoming Telemetry: Affiliate Payout Spike across Partner #AP-401 & Partner #AP-809
                                      │
                                      ▼
                    [Temporal Correlation & Trading Graph]
          1. Detects Opposite Trading: Referred clients of Partner A (23 accounts) take 
             simultaneous BUY positions on Boom 1000 while referred clients of Partner B 
             (23 accounts) take simultaneous SELL positions (Timing Correlation: 91.4%).
          2. Lockstep Profit Extraction: One side always wins, the other loses; positions 
             neutralize market risk while partners harvest guaranteed 40% RevShare payouts!
                                      │
                                      ▼
                    [Multi-Tier Sub-Affiliate Tree Traversal]
          • Graph reveals: Both Partner A and Partner B roll up to Master Partner #MP-007 
            through 3 hidden layers of sub-affiliates (SO compensation gaming).
          • Total Syndicate Scope: 7 Partners, 23 Sub-Affiliates, 184 Referred Accounts.
                                      │
                                      ▼
                    [Bonus Abuse & Client Quality Scoring]
          • Asserts Client Quality: 114 referred accounts deposited minimum $50, executed 
            exactly 1 micro-trade, and withdrew immediately (Bonus/CPA harvesting signature).
                                      │
                                      ▼
                    [Commission Financial Exposure Impact]
          • Quantifies exact damage: $42,500 unearned RevShare payouts over 45 days.
                                      │
                                      ▼
             [Governed Action: Two-Phase Commit Clawback & Freeze]
          • Proposes: [ 🛑 Halt Partner Commissions ] & [ ↩️ Clawback Unearned RevShare ]
```

#### Core Capabilities Realized in Module B:
1. **Opposite & Mirror Trading Detection:** Evaluates trade entry/exit millisecond timestamps and directional exposure across ostensibly unrelated affiliates, computing statistical correlation matrices.
2. **Multi-Level Relationship Mapping:** Visualizes complex partner hierarchies, sub-affiliate attribution chains, and client recycling (same person signing up under multiple affiliates).
3. **Client Quality Scoring & Bonus Abuse Guard:** Automatically scores referred traffic to detect bot sign-ups, fake traffic inflation, and deposit-trade-withdraw bonus harvesting.
4. **The "Blow Our Minds" Syndicate Revelation:** Identifies coordinated fraud rings spanning **7 partners, 23 sub-affiliates, and 184 referred clients**, isolating Master Partner #MP-007 as root cause.
5. **Financial Exposure Quantification & Governed Clawback:** Calculates exact unearned commission liability ($42,500) and executes cryptographically signed commission freezes via the Governed Action Bar.

---

### 5.3 Module C: Partner Churn Prediction & Early Warning Radar (Briefing 3)

Partner churn is invisible until it is irreversible: recruiting a replacement partner costs 5x more than retaining an existing one, and high-value master affiliates generate 80%+ of regional trading volumes.

```
Continuous Telemetry: 5,000+ Active Partners Ingested via Cloud Pub/Sub
                                      │
                                      ▼
                    [Silent Disengagement Indicator Engine]
          • Behavior Decay: Login frequency down 68% over 30 days.
          • Referral Volume Velocity: Weekly first-time depositors (FTD) down 45% MoM.
          • Traffic Quality Shift: Conversion rate drops from 8.2% to 1.4%.
                                      │
                                      ▼
                  [Multi-Signal Sentiment & Competitive NLP]
          • Communication Signals: 3 unresolved support tickets regarding payment gateway latency.
          • Competitor Poaching Signals: Partner feedback mentions "Exness lower EUR/USD spreads" 
            and "XM instant local withdrawal cashier".
                                      │
                                      ▼
                    [Churn Probability & Hazard Tiering]
          • Predicts: Partner #AP-1029 (Top 2% in LATAM, $120k/mo turnover) has 84% Churn Hazard!
          • Lead Time: Currently in Optimal Intervention Window (estimated 14 days before total churn).
                                      │
                                      ▼
                    [Cohort Systemic Anomaly Discovery]
          • Cohort Alert: "Warning: 8 tier-1 partners in Colombia showing identical disengagement 
            curves following local Payment Agent fee restructuring."
                                      │
                                      ▼
                  [Proactive AI-Prescribed Retention Playbook]
          • Suggests tailored action: 
            1. Automated VIP RevShare Tier Upgrade (from 35% -> 42%).
            2. Dedicated Relationship Manager outreach within 24 hours.
            3. Rerouting Colombian cashier traffic to higher-speed local payment rail.
          • Governed Action: [ 🎁 Deploy Retention Incentive & VIP Tier ]
```

#### Core Capabilities Realized in Module C:
1. **Silent Disengagement Early Warning:** Tracks subtle pre-churn indicators (login frequency, dashboard session length, referral trajectory) weeks before trading volume collapses.
2. **Multi-Signal Risk Scoring:** Fuses behavioral metrics, financial commission trajectories, support ticket sentiment, and competitor poaching NLP into an explainable **Churn Hazard Score (0-100)**.
3. **Cohort-Level Systemic Risk Detection:** Identifies geographic or regional partner cluster churn (e.g. LATAM payment friction or African currency devaluations) to distinguish systemic platform issues from individual disengagement.
4. **Optimal Intervention Window:** Flags the critical timeframe where manager intervention has highest ROI, before the partner redirects their traffic to rivals (Exness, XM).
5. **Proactive Retention Playbooks:** Recommends concrete commercial actions (commission re-tiering, bespoke CPA deals, dispute fast-tracking) directly executable from the executive cockpit.

---

### 5.4 The Fourth Flagship Capability: Executive Synthesis Engine (Cross-Domain Causal Briefing + Scenario Simulation + Morning Briefing)

Per §1.3 and `docs/red_team_findings.md` Findings 1–2, this is **not a fourth module** — it is the platform's organizing promise, sitting above Modules A/B/C and consuming their outputs plus the raw Financial and Competitive Intelligence data products none of the three modules otherwise touch. It is realized by three agents added to the Layer 3 mesh in §3 (Executive Synthesis Agent, Scenario Simulation Engine, Morning Briefing Generator).

#### Worked example (mirrors `docs/enterprise_briefing.md`, "What Would Blow Our Minds," bullet 1)

```
Trigger: Scheduled Morning Briefing job (Cloud Workflows, 06:00 broker-local) OR
         ad-hoc executive query: "Why is client LTV declining?"
                                      │
                                      ▼
                    [Executive Synthesis Agent — 4-Domain Traversal]
          1. omcp_execute_function("ltv_trend_30d") -> -12% QoQ (Financial/Client)
          2. omcp_traverse_links(metric="ltv_trend_30d", link_type="DRIVEN_BY_PARTNER_MIX")
             -> Partner mix shifted: Tier-1 (high LTV referrals) share down 18pp,
                Tier-3 (bonus-harvesting-prone) share up 18pp over the same window (Partner)
          3. omcp_execute_function("commission_competitiveness_index") -> -0.31 vs. Exness/XM
             (Competitive) — flagged as the point where Tier-1 partners began reallocating spend
          4. omcp_search_objects(type="CompetitorBenchmark", event="partner_payout_change")
             -> Exness raised affiliate RevShare from 35% -> 45%, 62 days prior (Competitive)
                                      │
                                      ▼
                    [Pearlian Causal DAG Evaluator — Chain Refutation]
          • SCM: [Competitor Payout ↑] -> [Partner Mix Shift] -> [Referral Quality ↓] -> [Client LTV ↓]
          • Each edge independently refuted (placebo test, p > 0.05) before the chain is asserted whole.
          • Escalation Rule (per CLAUDE.md Red Lines): any edge failing refutation (p ≤ 0.05 or
            confidence < 80%) demotes that hop to "correlation detected, insufficient data to
            assert causation" — the narrative is truncated at that hop, never asserted whole.
                                      │
                                      ▼
                    [Scenario Simulation Engine — Shock Injection]
          • Same DAG, do(competitor_payout = +10pp further): projects client acquisition cost
            +15%, top-20-partner defection risk, ranked defensive actions with ROI estimates.
                                      │
                                      ▼
                    [Metric Auditor Verification Gate]
          • Confirms every quoted number (-12%, 18pp, -0.31, 35%->45%, +15%) against live
            Cube Core / DuckDB scalars and cites the Ontology entity ID or Data Product
            timestamp backing it (Red Lines citation requirement).
                                      │
                                      ▼
                    [Morning Briefing Generator] (proactive, unprompted)
          "Good morning. Here's what changed overnight: Client LTV is declining because
           partner mix shifted toward lower-quality channels, which happened because our
           commission structure became uncompetitive after Exness raised partner payouts
           62 days ago. 1 opportunity: match the payout increase for Tier-1 partners only
           (ROI: retains ~$X in LTV at ~40% of the cost of a broad increase). Shall I elaborate?"
```

#### Core Capabilities Realized in the Executive Synthesis Engine:
1. **True 4-domain causal chains:** Competitive → Partner → Client → Financial in one refuted narrative, not four disconnected dashboard tiles — directly answering the briefing's highest-priority "blow our minds" bar.
2. **Scenario simulation via shock injection:** Reuses the same DoWhy SCM already in the stack (no new library) to answer "what if competitor X acquires competitor Y" with quantified downstream impact and ranked defensive actions.
3. **Proactive Morning Briefing:** A scheduled Cloud Workflows job runs the same synthesis pipeline unprompted and streams the result before an executive asks — the cockpit's only push (vs. pull) surface.
4. **Same governance guarantees as Modules A/B/C:** every quoted number still passes the Metric Auditor Gate; every causal hop still requires independent refutation; the same escalation-to-correlation-language rule applies per hop, not just per narrative.

---

## 6. QuantumBlack Design System (QBDS) Common Operational Picture

The frontend is an operational decision cockpit built with **Next.js 15, React 19**, and **QBDS** (`mckinsey/quantumblack-design-system`):

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  DERIV ENTERPRISE INTELLIGENCE OPERATING SYSTEM (EIOS)                                  [Active Role: Lead FDE]│
│  MODULES:  [ 🛡️ 1. Client Sentinel ]  •  [ ⚖️ 2. Partner Integrity ]  •  [ 📡 3. Partner Churn Radar ]  •  [ 📊 4. Executive Synthesis ]│
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  TRIAGE & ANOMALY INBOX              │  AI COPILOT DOSSIER & EVIDENCE SYNTHESIS  │  KINETIC NETWORK GRAPH      │
│  (Filtered by Risk / Churn Hazard)   │  (Powered by Gemini 3.8 Flash via SSE)    │  (React Flow Multi-Hop)     │
│                                      │                                           │                             │
│  [CRITICAL FRAUD] Account #CR84920   │  Client Dossier: Account #CR84920         │       [Master Ptr #007]     │
│  • Client Sentinel (Briefing 1)      │  • Risk Score: 89/100 (AML Discrepancy)   │               │             │
│  • Flag: Deposits 1,600% > Income    │  • Root Cause: Declared $500/mo income;   │      ┌────────┴────────┐    │
│  • 23-Account Syndicate Link         │    deposited $8,000 USDT via Crypto PA.   │      ▼                 ▼    │
│                                      │  • DoWhy Test: Placebo Refuter Confirmed. │  [Ptr A #401]     [Ptr B #809]
│  [PARTNER ABUSE] Syndicate Ring #14  │                                           │      │                 │    │
│  • Partner Integrity (Briefing 2)    │  Partner Dossier: Opposite Trading Ring   │      ▼ (23 BUYs)       ▼ (23 SELLs)
│  • Opposite Trading: Ptr A & B       │  • Scheme: 46 accounts paired on Boom 1000│  [23 Accts]       [23 Accts]
│  • Exposure: $42,500 unearned RevShare  • Unearned Commission Liability: $42,500 │       └───[:MATCHED_TIMING]──┘
│                                      │                                           │                             │
│  [CHURN HAZARD] Partner #AP-1029     │  Partner Churn Dossier: #AP-1029 (LATAM)  │  CHURN SIGNAL RADAR         │
│  • Partner Radar (Briefing 3)        │  • Churn Risk: 84% (Optimal Window: 14d)  │  • Login Decay: -68%        │
│  • Exness Competitor Poaching Signal │  • Root Cause: Payout ticket delays +     │  • Referral FTD: -45%       │
│  • Top 2% Regional Volume Contributor│    rival spread comparison (Exness).      │  • Sentiment: Frustrated    │
│                                      │                                           │                             │
│  [🌅 MORNING BRIEFING] Auto-Pushed   │  Executive Synthesis Dossier              │  4-DOMAIN CAUSAL CHAIN      │
│  • Executive Synthesis (§5.4)        │  • "Client LTV down 12% QoQ because       │  Competitive → Partner →    │
│  • 3 insights, 2 risks, 1 opportunity│    partner mix shifted after Exness       │  Client → Financial          │
│  • Unprompted, streamed at 06:00     │    raised payouts 62 days ago."           │  (What-If Shock Slider)      │
├──────────────────────────────────────┴───────────────────────────────────────────┴─────────────────────────────┤
│  GOVERNED ACTION BAR (Two-Phase Commit with HMAC-SHA256 Action Intent Token):                                  │
│  [ 🔒 Freeze Client Withdrawals ]  [ 🛑 Halt Partner Payouts & Clawback ]  [ 🎁 Deploy Retention VIP Deal ]  [ 📝 Generate SAR ]│
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**On the 4th tab:** v1 left "📊 Broker 360" as an undefined placeholder. It is now explicitly the **Executive Synthesis Engine's** home (§5.4) — the Morning Briefing feed, the 4-domain causal chain view, and the Scenario Simulation "what-if" shock slider, rather than a generic BI dashboard.

---

## 7. Cost-Optimized GCP Serverless Bill of Materials ($100 Envelope)

All components run on Google Cloud serverless infrastructure with **100% scale-to-zero**:

| Component | GCP Service | Sizing / Configuration | Idle Cost | Estimated Monthly Cost |
|---|---|---|---|---|
| **Ingestion Pipeline** | Cloud Pub/Sub | Serverless event bus (<10 GB/mo free tier) | $0.00 | $0.00 |
| **Streaming Micro-Batcher**| Cloud Run | 1 vCPU, 512MB RAM, min instances = 0 | $0.00 | $1.20 |
| **Ontology & Reasoning API**| Cloud Run | 2 vCPU, 2GB RAM, min instances = 0 | $0.00 | $4.50 |
| **Executive Cockpit (Next.js)**| Cloud Run | 1 vCPU, 1GB RAM, min instances = 0 | $0.00 | $2.80 |
| **Reasoning Model** | Vertex AI | Gemini 3.8 Flash via `google-genai` SDK ($0.075 / 1M tokens with prompt caching) | $0.00 | $3.50 (for ~20,000 queries) |
| **Analytical Lakehouse** | BigQuery On-Demand| 1 TB analysis free tier / mo; 10 GB free storage | $0.00 | $0.50 |
| **Action Orchestrator** | Cloud Workflows | 5,000 internal steps free / mo | $0.00 | $0.00 |
| **Lakehouse Object Store** | Cloud Storage (GCS)| Standard storage (Parquet files, ~5 GB) | $0.00 | $0.15 |
| **Total Estimated Footprint** | | | **$0.00/hr** | **~$12.65 / month** (Well within $100 credit!) |

---

## 8. Verification Matrix & Live Demonstration Flow

| Metric / Objective | Target Metric | Architectural Defense Mechanism |
|---|---|---|
| **Whole-Broker Intelligence** | 6 Unified Business Domains | Single Kinetic Enterprise Ontology spanning Client, Finance, Partner, Ops, Market, and Risk. |
| **Module A: Client Fraud** | Slashing 95% false alarms; 23-account ring | Predictive False-Positive Gate + DoWhy causal refutation + NetworkX multi-hop graph traversal. |
| **Module B: Partner Integrity** | Opposite trading ($r > 0.85$); 184 clients | Temporal correlation engine + multi-tier sub-affiliate tree traversal + unearned commission clawback. |
| **Module C: Partner Churn Radar**| 14-Day Early Warning Lead Time | Multi-signal hazard scoring (login decay, support sentiment, Exness poaching) + optimal window playbooks. |
| **4th Capability: Executive Synthesis** | True 4-domain causal chain (Competitive→Partner→Client→Financial) | Executive Synthesis Agent + Scenario Simulation Engine + Morning Briefing Generator, all gated by per-hop causal refutation (§5.4). |
| **Decision Learning Flywheel** | Recommendation quality improves over time, not just delivered once | `decision_outcomes_ledger` (BigQuery) with 30/60/90-day predicted-vs-actual reconciliation and causal-DAG edge-weight recalibration (§3, Layer 5). |
| **Synthetic-Data Provenance** | Zero hand-typed demo numbers | Every headline figure in this document and the demo script must trace to a `docs/synthetic_data_strategy.md` generator run at a stated `--seed` — no number may be typed directly into a component or fixture. |
| **Investigation Velocity** | 5x productivity improvement | 30-Second Investigation Copilot reduces review time from **90 minutes $\to$ 8 minutes**. |
| **Audit & Regulatory Compliance** | 100% compliant documentation | 1-Click SAR generator creating formatted reports adhering to Malta MFSA & Labuan LFSA specs. |
| **GCP Budget Compliance** | Total spend < $20.00 | Scale-to-zero serverless Cloud Run and pay-per-query BigQuery slots ($0/hr idle). |

---

### 8.1 The 3-Minute Live Hackathon Demonstration Script ("Must Demo Live")

To prove compliance with the hackathon's "Must Demo Live" requirement, the software executes a seamless 3-minute end-to-end demonstration flow opening with the platform's headline cross-domain promise, then showcasing the three integrated operational modules, and closing on the learning flywheel:

```
[0:00 - 0:30] 🌅 MORNING BRIEFING & 4-DOMAIN CAUSAL NARRATIVE (THE "BLOW OUR MINDS" OPENER)
• Open on [ 📊 4. Executive Synthesis ] — the Morning Briefing has already streamed, unprompted:
  "Good morning. Here's what changed overnight: Client LTV is declining because partner mix
   shifted toward lower-quality channels, which happened because our commission structure
   became uncompetitive after Exness raised partner payouts 62 days ago."
• Expand the causal chain visual: Competitive (Exness payout +10pp) → Partner (mix shift 18pp)
  → Client (LTV -12% QoQ), each hop independently DoWhy-refuted (p > 0.05) before assertion.
• Drag the What-If Shock Slider: "If competitor X acquires competitor Y" → projects +15% CAC,
  top-20-partner defection risk, ranked defensive actions (Scenario Simulation Engine, §5.4).

[0:30 - 0:55] WHOLE-BROKER EIOS COCKPIT & CUBE METRIC GOVERNANCE
• Demonstrate cross-domain navigation across all 6 domains: Client, Financial, Partner, Ops, Market, and Risk.
• Highlight live metrics (B-Book Synthetics yield, MT5 latency, DP2P escrow duration) served directly by Cube Core / DuckDB.

[0:55 - 1:30] MODULE A: CLIENT FRAUD SENTINEL (BRIEFING 1)
• Switch to [ 🛡️ Client Sentinel ].
• Show the 95% False-Positive Reduction in action:
  - Benign VIP Scalper (#12093) auto-resolved with a green audit badge ("Income verified via tax return, DoWhy causal test refutes fraud").
  - Account #CR84920 flagged with Risk Score 89 (Deposits 1,600% above declared income, Frankfurt VPN, 3 DP2P disputes).
• Click Account #CR84920: Gemini 3.8 Flash streams a structured 30-second case dossier via SSE (/api/v1/stream).
• React Flow renders the 23-Account Syndicate Ring sharing 3 WebGL device fingerprints and 1 Payment Agent.

[1:30 - 2:05] MODULE B: PARTNER INTEGRITY & OPPOSITE TRADING (BRIEFING 2)
• Switch to [ ⚖️ Partner Integrity ].
• Inspect Alert: "Opposite Trading Syndicate #14: Partner A (#401) & Partner B (#809)".
• Evidence Synthesis: Show 46 accounts executing opposite BUY/SELL positions on Boom 1000 with 91.4% timing correlation.
• Multi-Tier Sub-Affiliate Tree: Expand the hierarchy to reveal Master Partner #MP-007 orchestrating across 3 tiers.
• Financial Exposure: System quantifies $42,500 in unearned commissions.
• Click [ 🛑 Halt Partner Payouts & Clawback ]: Two-Phase Commit token locks payouts instantly.

[2:05 - 2:35] MODULE C: PARTNER CHURN RADAR & RETENTION (BRIEFING 3)
• Switch to [ 📡 Partner Churn Radar ].
• View Triage: Top LATAM Partner #AP-1029 ($120k/mo volume) flagged at 84% Churn Hazard.
• Explainable AI Drivers:
  - Behavior: 68% drop in dashboard logins over 30 days.
  - Sentiment: Frustrated support tickets regarding payment gateway delays.
  - Competitor Poaching NLP: Partner explicitly cited Exness tighter spreads.
• Cohort Risk Warning: System highlights 8 Colombian partners exhibiting identical drop-offs.
• Click [ 🎁 Deploy Retention VIP Deal ]: Generates custom retention package (42% RevShare tier + priority cashier routing) during the 14-day optimal intervention window.

[2:35 - 3:00] GOVERNED WRITE-BACKS, 1-CLICK REGULATORY SAR & THE LEARNING FLYWHEEL
• Click [ 📝 Generate Regulatory SAR ]:
  - Gemini 3.8 Flash generates an audit-ready Suspicious Activity Report (MFSA / LFSA format) for Account #CR84920 and Syndicate #14 with cryptographic citation hashes.
• BigQuery Ledger: Show immutable audit logs recorded for continuous model retraining.
• Show the `decision_outcomes_ledger`: last week's retention playbook for Partner #AP-0812 is
  reconciled against its 30-day actual outcome, and the causal DAG's edge weight is shown
  recalibrating in response — the flywheel closing the loop, not just logging a decision.
• Conclude: "3 Deriv challenges solved plus true 4-domain executive synthesis, in 1 unified operating system; 5x productivity gain; 100% serverless scale-to-zero."
```

---

## 9. Known Limitations & Open Risks

This section is new in v2 and is deliberately not resolved — it exists so that whoever decomposes this document into spec-kit tasks inherits the same risk picture this red-team pass surfaced, rather than treating v2 as fully verified. Full rationale for each item is in `docs/red_team_findings.md`.

1. **Module A has no verified local ground truth (Finding 6, unresolved).** Briefing 1 is a Google-Drive PDF that could not be accessed; unlike Modules B and C, no `scratch/briefings/b1_full.txt` exists in this repository. Every Module A figure in §5.1 (95% false-positive reduction, `<450ms` synthesis, the 23-account/3-device/1-PA ring shape) is inherited from general Palantir/AML pattern-matching conventions, not a confirmed requirement. **Action before implementation:** capture the real Briefing 1 text the same way `b2_full.txt`/`b3_full.txt` were captured, and re-validate §5.1's scope against it.
2. **Module C's target figures are illustrative, not briefing-derived (Finding 4).** `b3_full.txt` contains no numeric example analogous to `b2_full.txt`'s "7 partners, 23 sub-affiliates, 184 clients." The 84% Churn Hazard, Partner #AP-1029, and the Colombia cohort in §5.3 are an internally consistent illustrative scenario (see `docs/synthetic_data_strategy.md`'s Module C generation spec, explicitly labeled as such), engineered to be plausible rather than sourced.
3. **Layer 0 (synthetic data) is specified but not yet implemented.** `docs/synthetic_data_strategy.md` defines the generator design and the hard rule that every headline number must trace to a seeded run; no generator code exists yet. Until it does, every number in this document remains a target to engineer toward, not a demoed output.
4. **The Executive Synthesis Engine's 4-hop causal chain is the highest-complexity component in the platform.** It requires all three of Modules A/B/C's causal machinery plus two additional domains (Financial, Competitive) it doesn't otherwise touch, chained through independent refutation at each hop (§5.4). This is new integration surface, not a recombination of already-built pieces — budget implementation risk accordingly relative to Modules A/B/C.
5. **The Decision Learning Flywheel's 30/60/90-day reconciliation cannot be demoed at real elapsed time.** Per `docs/synthetic_data_strategy.md`, "actual" outcomes for `decision_outcomes_ledger` must themselves be simulated forward from the same seed rather than waited out in real time — this is a deliberate design choice, not a gap, but it means the flywheel demo in §8.1 shows simulated reconciliation, not a genuinely time-elapsed one.


