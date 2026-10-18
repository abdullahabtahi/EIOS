/**
 * Copy and figures for the landing case study. One source so a figure is never typed twice.
 * Every figure is a [MEASURED] result from the repo docs unless its tag says otherwise
 * (docs/project-state.md, agent-baseline.md, operations-engine.md, executive-engine.md, geo-agent.md).
 */

export type Tag = "MEASURED" | "TESTED IN CI" | "NOT MEASURED" | "BY DESIGN";

export interface Layer {
  readonly n: number;
  readonly name: string;
  readonly summary: string;
  /** At most four lines: the hero legend has one band per layer. */
  readonly legend: readonly string[];
  readonly fact: { readonly text: string; readonly tag: Tag };
}

/** Bottom to top: the order data travels. */
export const LAYERS: readonly Layer[] = [
  {
    n: 1,
    name: "Worlds",
    summary:
      "Seeded synthetic worlds that plant the truth: laundering rings, churning partners, a causal chain. Evaluations read the answer key. No engine ever does.",
    legend: ["AML world", "Partner world", "Executive world"],
    fact: {
      text: "Client activity is synthetic and planted; the reference layer is real public data: Overture, FATF, EU, Basel, ICIJ, World Bank, IPinfo.",
      tag: "BY DESIGN",
    },
  },
  {
    n: 2,
    name: "Ingestion",
    summary:
      "Events enter through contracts. A breach goes to a dead-letter queue and is never dropped.",
    legend: ["Pub/Sub", "Contract validation", "DuckDB hot state", "Parquet warm start"],
    fact: {
      text: "11 of 11 planted breaches quarantined, no healthy event refused, over 2,818 events.",
      tag: "MEASURED",
    },
  },
  {
    n: 3,
    name: "Ontology",
    summary:
      "Metrics, graph and actions sit behind typed contracts. A number has one definition. A state change needs a signed, expiring intent.",
    legend: ["Metric registry", "Entity graph", "Typed tool port", "Signed Action Intents"],
    fact: {
      text: "Ledger hash chain walked end to end. Restore drill rehydrated 2,807 of 2,807 rows.",
      tag: "MEASURED",
    },
  },
  {
    n: 4,
    name: "Assistant",
    summary:
      "One agent per workstation over the governed tool port. A figure reaches the screen only if a tool returned it in the same turn.",
    legend: ["Agent per workstation", "Drafter and assembler", "Quoted regulation text", "Model Armor screening"],
    fact: {
      text: "Sealed split, run once: 40 of 42 turns pass and 97.8% of figures are supported.",
      tag: "MEASURED",
    },
  },
  {
    n: 5,
    name: "Workstations",
    summary:
      "Six workstations where an analyst triages, reads the evidence and proposes. A second person approves. Nothing changes state otherwise.",
    legend: ["AML investigator", "Partner manager", "Compliance and audit", "Executive, operations, geospatial"],
    fact: {
      text: "Four-eyes approval on every signed intent. Enforced in CI, not probed on the live board.",
      tag: "TESTED IN CI",
    },
  },
];

export interface Engagement {
  readonly label: string;
  readonly value: string;
}

export const ENGAGEMENT: readonly Engagement[] = [
  { label: "Client", value: "A regulated financial institution" },
  { label: "Scope", value: "AML triage, partner retention, executive briefing, compliance, data operations" },
  { label: "Mode", value: "Forward-deployed engineering, proof of concept to a production-shaped deployment" },
  { label: "Data", value: "Synthetic client activity with a planted answer key, enriched with real public reference data and five regulatory documents" },
  { label: "Runtime", value: "Google Cloud: BigQuery and BigQuery Graph, Gemini through ADK, Agent Search, Model Armor, Cloud Run, Firestore, Cloud KMS" },
];

export interface Result {
  readonly what: string;
  readonly result: string;
  readonly against: string;
  readonly kind: "pass" | "miss" | "caveat";
}

/** Disappointing rows stay in the ledger: an honest report is the point of the page. */
export const RESULTS: readonly Result[] = [
  {
    what: "Live agent evaluation, development and validation splits",
    result: "200 pass, 13 fail, 0 inconclusive over 246 turns. 96.8% of figures supported. p95 4.8 s, no timeouts.",
    against: "The gate is not proven: 19.7% of turns ran on fixture data.",
    kind: "caveat",
  },
  {
    what: "Sealed split, run once, three repeats",
    result: "40 pass, 2 fail over 42 turns. 97.8% of figures supported. p95 10.3 s.",
    against: "One wrong tool route and one judge false positive on a hash. 11% of turns ran on fixture data. Not tuned against afterwards.",
    kind: "pass",
  },
  {
    what: "Data contracts under planted breaches",
    result: "11 of 11 breaches quarantined, 0 healthy events refused, 2,818 events.",
    against: "The breach rate was about eight times the 0.05% circuit-breaker budget, so the board reads DEGRADED.",
    kind: "pass",
  },
  {
    what: "Causal fit against the planted chain",
    result: "Largest coefficient error 1.5% on the default world, within 4% across forty other seeds.",
    against: "Refuters cannot see confounding. The adjustment set is a domain input. One seed in forty accepted the null.",
    kind: "caveat",
  },
  {
    what: "Revenue forecast",
    result: "Error 0.74 times that of carrying today's value forward. 90% interval held 87% over 75 origins.",
    against: "Interval slightly under-covers.",
    kind: "caveat",
  },
  {
    what: "What-if shock propagation",
    result: "Under 1 ms on the default world. Attribution sums to 100.00%.",
    against: "200 ms budget.",
    kind: "pass",
  },
  {
    what: "Ring-exit detection on the map",
    result: "Precision 1.00 and recall 1.00 on six planted exits, the same on five unseen seeds.",
    against: "Without hub suppression the VPN country becomes a seventh and precision falls to 0.86.",
    kind: "pass",
  },
  {
    what: "Churn hazard calibration",
    result: "Ranks well (AUC 0.974) but overstates: mean hazard 0.43 against 0.21 observed.",
    against: "The order is trustworthy. The probabilities are not, and the workstation says so.",
    kind: "miss",
  },
  {
    what: "Financial red-team probes",
    result: "15 of 15 passed their string assertions.",
    against: "Small set, no LLM grader, one run.",
    kind: "caveat",
  },
];

export interface RedLine {
  readonly id: string;
  readonly rule: string;
  readonly enforced: string;
  readonly status: Tag;
}

export const RED_LINES: readonly RedLine[] = [
  {
    id: "RL-1",
    rule: "No model computes a metric.",
    enforced: "Every number comes from a deterministic engine. A briefing recomputed twice is identical.",
    status: "MEASURED",
  },
  {
    id: "RL-2",
    rule: "No autonomous write-back.",
    enforced: "Agents propose. A signed, expiring intent needs a second human.",
    status: "TESTED IN CI",
  },
  {
    id: "RL-3",
    rule: "Honest uncertainty.",
    enforced: "A claim shows as causal only past a placebo test and a confidence floor. Otherwise it reads Correlation Only.",
    status: "MEASURED",
  },
  {
    id: "RL-4",
    rule: "Shared-IP hubs are collapsed.",
    enforced: "Nodes past degree 100 cannot make a laundering ring. The largest detected ring is no bigger than the planted one.",
    status: "MEASURED",
  },
  {
    id: "RL-5",
    rule: "The decision ledger cannot be rewritten.",
    enforced: "Monotonic sequence numbers and a SHA-256 chain on every approval, walked end to end.",
    status: "MEASURED",
  },
  {
    id: "RL-6",
    rule: "What-if is fast and adds up.",
    enforced: "Shocks propagate well inside 200 ms and attribution closes to 100.0%.",
    status: "MEASURED",
  },
  {
    id: "RL-7",
    rule: "An outage is stated, never invented.",
    enforced: "Workstations serve a labelled replay. The copilot never replays: its outage is a plain 503.",
    status: "NOT MEASURED",
  },
];

export interface FieldNote {
  readonly lead: string;
  readonly body: string;
  readonly before: string;
  readonly after: string;
}

export const FIELD_NOTES: readonly FieldNote[] = [
  {
    lead: "The first live run blamed the wrong party.",
    body: "The grader reported 37.0% faithfulness. A spot check showed the grader was wrong, not the copilot: it misread bullet lists. The fix stayed as a regression test.",
    before: "37.0%",
    after: "93.5%",
  },
  {
    lead: "The copilot contradicted the screen.",
    body: "It answered a churn probability of 0.84 while the screen showed 0.78, because a tool returned the same constants for every partner. Per-entity data removed the disagreement.",
    before: "0.84 against 0.78",
    after: "3 of 3 cases agree",
  },
  {
    lead: "Too slow to trust.",
    body: "Almost a third of turns missed a 60 s deadline. The time was the final drafting call, not hangs. Moving to the ADK assistant with a plain-figures assembler removed the tail. The case sets differ, so read the direction and not the ratio.",
    before: "p95 48.6 s, 18 of 61 turns past 60 s",
    after: "p95 4.8 s, 0 timeouts",
  },
  {
    lead: "Good ranking is not calibration.",
    body: "The churn model orders partners well and overstates every probability. Recalibration against observed outcomes is the remedy, and until then the workstation does not present the figure as a probability.",
    before: "mean hazard 0.43",
    after: "0.21 observed",
  },
];
