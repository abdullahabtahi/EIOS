# McKinsey & QuantumBlack Financial Services Insights Report
## Empirical Research on Banking, Capital Markets Architecture, and Network AML
**Author:** Forward Deployed Engineering (FDE) Research Cell  
**Source:** [McKinsey Financial Services Our Insights](https://www.mckinsey.com/industries/financial-services/our-insights) (Global Banking Reviews, QuantumBlack Fraud Analytics, Network Science in AML)  
**Focus:** Infusing McKinsey & QuantumBlack Financial Industry Standards into the Deriv Enterprise Intelligence Operating System (EIOS)  

---

## 1. Executive Summary

McKinsey & Company’s global financial services research and QuantumBlack’s field deployments reveal the foundational requirements for modern institutional data platforms:

1. **The False-Positive AML Crisis (98% Failure Rate):** Traditional rules-based customer risk rating and transaction monitoring generate **over 98% false positives**, overwhelming compliance teams and blinding institutions to coordinated networks of illicit actors.
2. **Network Science as the Antidote:** Overcoming the 98% false-positive crisis requires shifting from isolated individual account monitoring to **Network Analytics & Community Detection** that uncover subcomponents of interconnected syndicates sharing devices, IPs, and payment conduits.
3. **QuantumBlack's 95% Fraud Loss Recovery Benchmark:** In a landmark deployment for a major UK bank, QuantumBlack combined cross-channel transaction data with historical fraud typologies using proprietary machine learning algorithms, successfully identifying **86% of fraud incidents and recovering 95% of total estimated financial losses**.
4. **Capital Markets Architecture as a Competitive Moat:** In capital markets and trading venues, data architecture directly dictates balance-sheet capital efficiency. McKinsey estimates that modernizing data and application architecture saves tier-1 institutions hundreds of millions annually in capital exposure and cuts trade booking errors, while boosting front-office producer efficiency by up to **8x**.
5. **GenAI as an Operational Risk Expert:** Leading institutions are moving away from artisan point-solutions to industrial GenAI frameworks where models act as "virtual risk experts"—reading regulatory updates, synthesizing complex customer profiles, and drafting audit-ready filings for human decision-makers.

---

## 2. Key Case Studies & Benchmarks from McKinsey Financial Services

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    MCKINSEY & QUANTUMBLACK FINANCIAL DEPLOYMENT BENCHMARKS                      │
├───────────────────────────────┬─────────────────────────────────┬───────────────────────────────┤
│ Domain / Research Body        │ Structural Finding & Innovation │ Quantified Operational Impact │
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 1. QuantumBlack UK Bank       │ Unified cross-channel payment   │ • 95% of estimated fraud      │
│    Fraud Transformation       │ telemetry with historical fraud │   financial loss recovered    │
│    ("Fraud Management")       │ cases to build risk scores.     │ • 86% of fraud incidents      │
│                               │ Integrated multi-channel policy.│   accurately identified       │
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 2. Network Analytics in AML   │ Transitioned from individual    │ • Directly counters the 98%+  │
│    ("Banking Matters AML")    │ static thresholds to community  │   false-positive rate         │
│                               │ detection and graph analytics   │ • Uncovers coordinated rings  │
│                               │ linking accounts, IPs, devices. │   splitting small transactions│
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 3. Capital Markets            │ Modernized core data and        │ • Up to $300M/yr in capital   │
│    Architecture Value         │ application topology to support │   savings (RWA reduction)     │
│    ("Foundation for Value")   │ real-time trade surveillance.   │ • 8x front-office efficiency  │
│                               │ Automated exception handling.   │ • 4x post-trade FTE throughput│
├───────────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ 4. GenAI in Corporate &       │ Scaled GenAI "virtual risk      │ • 20% to 30% capacity created │
│    Investment Banking (CIB)   │ experts" for compliance triage, │   in middle/back office       │
│    ("Been There, Doing That") │ regulatory report synthesis, and│ • Automated model documentation│
│                               │ real-time FX/liquidity advisory.│ • Human-in-the-loop governance│
└───────────────────────────────┴─────────────────────────────────┴───────────────────────────────┘
```

---

## 3. Four Core McKinsey Insights Applied to Deriv EIOS

### 3.1 Network Science to Defeat the 98% False-Positive Barrier
- **McKinsey Insight:** Conventional AML monitoring looks at individual transactions (e.g. deposit > $10,000). Fraudsters easily evade this by smurfing—breaking illicit funds into small, non-rounded amounts spread across dozens of related accounts. Relational SQL queries miss these connections, driving false positives above 98%.
- **Deriv Application:** In **Deriv Sentinel**, our graph engine analyzes the subcomponents of the customer network. When Account #CR84920 deposits $8,000, the system does not evaluate the deposit in isolation; it traverses the graph to find that **3 devices and 1 Payment Agent are coordinating transaction timing across 23 accounts**, proving organized syndication.

### 3.2 The QuantumBlack Integrated Fraud Strategy (Ending the "Squeezing a Balloon" Effect)
- **McKinsey Insight:** Focusing fraud prevention on a single channel (e.g. credit card cashier) simply squeezes the balloon, causing fraudsters to migrate to alternative payment rails (e.g. P2P or mobile). Furthermore, 20% of legitimate customers abandon onboarding due to clumsy, high-friction authentication.
- **Deriv Application:** Deriv EIOS establishes an integrated fraud strategy across all six business domains and cashier channels: **MetaTrader 5 CFDs, Deriv Trader Synthetics, Deriv P2P (DP2P), and local Payment Agents**. Authentication friction is minimized by utilizing automated passive device fingerprinting (WebGL/Canvas) and only triggering **Biometric Step-Up Liveness** when the causal fraud probability exceeds threshold.

### 3.3 Capital Efficiency & Real-Time Trade Surveillance
- **McKinsey Insight:** In trading and capital markets, data architecture renewal directly drives capital optimization. Clean, real-time data topology prevents overly conservative risk assumptions and mismatches in quarterly true-ups, significantly reducing Risk-Weighted Assets (RWA) and operational trade booking shortfalls.
- **Deriv Application:** In Deriv’s **Financial & Operational Intelligence domains**, the EIOS continuously tracks Deriv’s **Net Dealer Book Capital at Risk** across its proprietary Derived Indices (Volatility 100, Boom 1000). Sub-second tick aggregation prevents risk warehousing over-exposure, safeguarding broker clearing margins.

### 3.4 GenAI as the "Virtual Risk Expert" and Compliance Copilot
- **McKinsey Insight:** GenAI in banking must not be an unconstrained conversational chatbot. It must act as a **Virtual Risk Expert** that assists human officers: reading dense regulatory filings, synthesizing customer background dossiers, identifying relevant compliance requirements, and drafting audit-ready documentation.
- **Deriv Application:** The **30-Second Investigation Copilot** in Deriv Sentinel operationalizes this exact paradigm. It ingests fragmented logs and automatically drafts an audit-ready **Suspicious Activity Report (SAR)** formatted specifically for **Malta MFSA (ESMA rules)** and **Labuan LFSA**, ready for human sign-off in 1 click.

---

## 4. Integration into the Master Architecture (`initial_plan.md`)

These McKinsey insights reinforce the exact dual structure of our architecture:
1. **The Operating System (Deriv EIOS):** Provides the unified data topology, cross-domain semantic layers, and real-time capital surveillance recommended in McKinsey's *Capital Markets Architecture* framework.
2. **The Sentinel Feature Module:** Directly operationalizes McKinsey's *Network Analytics in AML* and QuantumBlack's *Integrated Fraud Management* benchmarks, cutting the 98% false-positive rate down to actionable, high-conviction cases.
