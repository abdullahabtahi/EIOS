# Red-Team Review of `initial_plan.md` (v1 → v2)

**Reviewer lens:** QuantumBlack Senior Partner × Palantir Forward Deployed Engineer × GCP Solution Architect
**Ground truth consulted:** `docs/enterprise_briefing.md` (primary — the actual hackathon master brief), `scratch/briefings/b2_full.txt`, `scratch/briefings/b3_full.txt`, `docs/foundry.md`, `.agents/skills/mckinsey-rewired-2nd/` (SKILL.md + all `references/*`)
**Not consulted (inaccessible):** the QuantumBlack Medium article (403) and the Google-Drive-hosted PDF briefings linked from `initial_plan.md` §1.2 (sign-in required). Findings that touch those links are flagged explicitly below rather than guessed.

This document records *why* `initial_plan.md` changed the way it did. Treat it as provenance for the spec-kit decomposition that follows — it is not itself part of the architecture.

---

## Method

1. Read the actual master briefing the hackathon issued (`docs/enterprise_briefing.md`) as primary ground truth, superseding any assumption baked into v1.
2. Cross-checked each of the three flagship modules in `initial_plan.md` §5 against the one local source document that actually specifies it (`b2_full.txt` for Module B, `b3_full.txt` for Module C). No local source exists for Module A.
3. Checked `initial_plan.md`'s use of Palantir/Foundry terminology against the real Foundry architecture in `docs/foundry.md`.
4. Checked `initial_plan.md`'s architectural framing against the deeper McKinsey Rewired reference material in `.agents/skills/mckinsey-rewired-2nd/references/` (causal inference, decision flywheel, AI platform mesh) that v1 evidently drew its language from but did not fully operationalize.

---

## Finding 1 (Critical) — The platform's headline capability is missing

`docs/enterprise_briefing.md` states the single most important bar for the whole platform, twice:

> *"Client LTV is declining because partner mix shifted toward lower-quality channels, which happened because our commission structure became uncompetitive after competitor X raised partner payouts."*
> — What Would Blow Our Minds, bullet 1

> *"Client acquisition costs rose because competitor X dropped pricing in Region Y, causing our partner referral quality to decline."*
> — Opportunity, Capability 2

Both are **one causal chain spanning four domains at once**: Competitive → Partner → Client → Financial. Neither `initial_plan.md`'s three modules, nor any combination of them running side-by-side, produces this. Module A reasons within Client+Compliance. Module B reasons within Partner+Client (trading telemetry). Module C reasons within Partner+Competitive (poaching NLP). **None of them ever touches Financial P&L, and none synthesizes across more than two domains in a single narrative.**

A demo that only shows three independent fraud/churn tools — however impressive individually — does not demonstrate the thing the brief explicitly says will "blow our minds." This is the single highest-leverage gap to close.

**Fix in v2:** a fourth, non-module capability — the **Executive Synthesis Engine** — that sits above Modules A/B/C and composes their outputs (plus raw Financial and Competitive data products they don't otherwise use) into the exact class of cross-domain causal chain the brief describes. See `initial_plan.md` new §5.4.

---

## Finding 2 (Critical) — Scenario Simulation and the proactive Morning Briefing are absent

Two more explicit "blow our minds" bullets have no home in v1:

- *"If competitor X acquires competitor Y, model shows: client acquisition costs +15%, partner defection risk for top 20 partners..."* — capability 3 (Predictive Analytics & Scenario Modelling) in the brief, entirely missing from v1's reasoning mesh.
- *"Good morning. Here's what changed overnight: 3 insights requiring attention..."* — proactive, unprompted synthesis. v1's cockpit is pull-only (an investigator opens a case); nothing pushes.

**Fix in v2:** added a Scenario Simulation Engine (shock-injection on the same DoWhy causal DAG already in the stack — no new library required) and a Morning Briefing Generator (scheduled Cloud Workflows job that runs the Executive Synthesis Engine proactively and streams the result before anyone asks). See §5.4.

---

## Finding 3 (High) — The Ontology was implicitly conflated with the semantic layer

`docs/foundry.md` is explicit: **"The Ontology is not a semantic layer."** The Ontology is the four-fold integration of data, logic, action, and security (object types, link types, action types, functions) — the semantic layer (Cube Core in this stack) is only the quantitative slice of it. `initial_plan.md` §3 Layer 2 labels its two engines "Quantitative Metric Layer" and "Topological Property Graph" and calls the thing that unifies them the "Ontology API" — this is *directionally* correct but under-labels the Ontology's other two legs (Action Types, Security/Markings), which live entirely in Layer 5 with no explicit link back to "this is part of the same Ontology." A reader unfamiliar with Foundry would come away thinking Ontology == metrics + graph.

**Fix in v2:** no structural change needed — Layers 2 and 5 already do the right thing — but added one clarifying sentence in §3 tying Action Types and Markings/RBAC explicitly back to the Ontology's four-fold definition, so the terminology doesn't drift for whoever implements this from spec-kit tasks later.

---

## Finding 4 (High) — No synthetic data generation strategy, anywhere

This is the most severe *credibility* gap, not just a completeness gap. The brief's own constraint table says **"Must demo live"** and **"Real-time processing... must reflect the current state, not yesterday's data."** There is no production Deriv system this team has access to. Every specific number that appears in `initial_plan.md`'s demo script — `Account #CR84920`, risk score `89`, `23-account syndicate`, `$42,500 unearned RevShare`, `84% Churn Hazard` for `Partner #AP-1029` — reads as a **scripted, hardcoded outcome**, because v1 never specifies where the underlying data (that these numbers are computed from) actually comes from.

Two of those numbers are legitimately traceable to source material — `b2_full.txt`'s own "What Would Blow Our Minds" section literally says *"Detected coordinated network: 7 partners, 23 sub-affiliates, 184 referred clients"* and *"Partner A refers 47 clients; 23 consistently take opposite positions... timing correlation: 89%"* — so Module B's target figures aren't invented from nothing, they're drawn from the briefing's own illustrative example. That's a reasonable target to engineer the demo dataset toward. But `b3_full.txt` contains **no equivalent numeric example** — no "84%," no "#AP-1029" — so Module C's specific figures in v1 appear to be invented outright. Module A has no local source document at all (see Finding 6), so its numbers are entirely unverifiable.

Either way, the deeper problem is the same regardless of where the target numbers came from: **v1 never states that these are the *output* of a generator rather than strings typed into a mock UI.** Palantir's own Foundry ships a purpose-built answer to exactly this problem — **Pilot**, which generates seed data in an isolated container specifically so that a demo can be built and an AI agent can operate on data *before* real enterprise access exists, without ever touching production (`docs/foundry.md` §Pilot). That is the precedent to cite and copy.

**Fix in v2:** added **Layer 0 — Synthetic Enterprise Data Foundry**, a documented, seeded, reproducible generator that produces every domain's dataset with the target fraud/churn patterns embedded by construction (not hand-typed), so the numbers in the demo script are provably the output of a pipeline. Full methodology broken out into `docs/synthetic_data_strategy.md` to keep `initial_plan.md` from ballooning. `initial_plan.md` §3 and §8 now reference it and require every headline demo number to cite its generator seed.

---

## Finding 5 (Medium) — Decision Learning Flywheel is present but not first-class

The brief's closing capability is explicit: *"Learning from decisions: Platform tracks which recommendations were implemented and their outcomes, improving future suggestions."* `initial_plan.md` v1 has a "Closed-Loop Continuous Learning Flywheel" bullet in the Layer 5 diagram box (§3, line ~163) and a BigQuery "30-Day Decision Attribution Ledger" — but no schema, no reconciliation algorithm, and no description of *how* an outcome updates a future recommendation's confidence. `.agents/skills/mckinsey-rewired-2nd/references/decision-learning-flywheel.md` already contains a complete, ready-to-adopt design for this (a `decision_outcomes_ledger` BigQuery table with predicted vs. actual columns at 30/60/90 days, plus a causal-DAG edge-weight recalibration rule keyed on forecast error).

**Fix in v2:** promoted the flywheel to an explicit, schema-bearing subsection of Layer 5, adopting the reference design directly (attribution below).

---

## Finding 6 (Medium, unresolved — flagging rather than fixing) — Module A has no local ground truth

`initial_plan.md` §1.2 sources Module A to a Google-Drive PDF ("Briefing 1") that is not present anywhere in this repository and could not be fetched (sign-in required). Modules B and C both have a corresponding `scratch/briefings/b{2,3}_full.txt` — no `b1_full.txt` exists. This means **Module A's entire scope (95% false-positive reduction, 30-second dossier, 23-account ring, SAR generation) is unverifiable against any source this reviewer can access**, and may be inherited from general Palantir/AML pattern-matching rather than the actual Briefing 1 requirements.

**This is not fixed in v2** — it cannot be, without the source document. v2 adds an explicit caveat at the top of §5.1 so this risk is not silently carried forward into spec-kit tasks as if it were verified. Recommended action for the user: obtain the actual Briefing 1 text (the same way `b2_full.txt`/`b3_full.txt` were captured) and re-validate Module A's scope before it is decomposed into implementation specs.

---

## Finding 7 (Low) — "5-Layer" vs. the skill's "4-Tier" framing

`initial_plan.md` uses a 5-Layer topology; `.agents/skills/mckinsey-rewired-2nd/SKILL.md` teaches a 4-Tier architecture. They describe the same system — the skill merges what `initial_plan.md` splits into Layers 4/5 into a single Tier 4 (Cockpit + Write-Back Hub), and doesn't have a separate ingestion/ontology split. No functional conflict, just a naming mismatch that could confuse whoever writes spec-kit tasks against both documents.

**Fix in v2:** one-line mapping note added to `initial_plan.md` §3 ("Layers 1–2 ≈ Tier 1–2A/2B, Layer 3 ≈ Tier 3, Layers 4–5 ≈ Tier 4A/4B") rather than renaming either document.

---

## Summary of v2 changes to `initial_plan.md`

| # | Change | Section |
|---|---|---|
| 1 | Added Layer 0: Synthetic Enterprise Data Foundry | §3, new |
| 2 | Added §5.4: Executive Synthesis Engine (cross-domain causal narrative, scenario simulation, morning briefing) | §5.4, new |
| 3 | Promoted Decision Learning Flywheel to schema-bearing subsection | §5 / Layer 5 |
| 4 | Clarified Ontology ≠ semantic layer (four-fold definition) | §3 |
| 5 | Added Module A ground-truth caveat | §5.1 |
| 6 | Added Layer/Tier naming reconciliation note | §3 |
| 7 | Updated demo script to open with Morning Briefing + cross-domain narrative | §8.1 |
| 8 | Added synthetic-data provenance requirement to Verification Matrix | §8 |

See `docs/synthetic_data_strategy.md` for the Layer 0 design in full.
