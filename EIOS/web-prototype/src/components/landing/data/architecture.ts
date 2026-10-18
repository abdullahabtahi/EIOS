/**
 * The EIOS architecture as drawn on the landing page. Components, Google Cloud services and paths are read from
 * the repo (EIOS/src/eios, EIOS/infra, docs/agent-architecture.md, the 2026-10-17 agent architecture artifact).
 */

export type GroupId = "workstations" | "agents" | "apis" | "ontology" | "data" | "logic" | "action";

export interface ArchGroup {
  readonly id: GroupId;
  readonly label: string;
  readonly tier: "top" | "mid" | "bottom";
}

export interface ArchNode {
  readonly id: string;
  readonly group: GroupId;
  readonly label: string;
  readonly desc: string;
  readonly gcp: readonly string[];
  readonly path?: string;
  /** A real catalogue query, shown verbatim in the inspector. */
  readonly query?: string;
}

export const GROUPS: readonly ArchGroup[] = [
  { id: "workstations", label: "Workstations", tier: "top" },
  { id: "agents", label: "Agents · Google ADK", tier: "top" },
  { id: "apis", label: "Gateway + APIs", tier: "top" },
  { id: "ontology", label: "Ontology · governed tool port", tier: "mid" },
  { id: "data", label: "Data sources", tier: "bottom" },
  { id: "logic", label: "Logic · engines", tier: "bottom" },
  { id: "action", label: "Systems of action", tier: "bottom" },
];

export const NODES: readonly ArchNode[] = [
  { id: "ws-aml", group: "workstations", label: "AML investigator", desc: "Triage queue, one-screen evidence dossier, network graph and a near-final SAR draft.", gcp: ["Cloud Run", "Identity Platform"], path: "web-prototype/src/components/cockpit" },
  { id: "ws-partner", group: "workstations", label: "Partner manager", desc: "Churn hazard radar against value at risk, cohort matrix and the sub-affiliate tree.", gcp: ["Cloud Run"] },
  { id: "ws-exec", group: "workstations", label: "Executive", desc: "Fitted causal graph, backtested forecast and the what-if with attribution.", gcp: ["Cloud Run"] },
  { id: "ws-comp", group: "workstations", label: "Compliance & audit", desc: "The WORM ledger, a hash-chain verifier and recovery proofs.", gcp: ["Cloud Run"] },
  { id: "ws-ops", group: "workstations", label: "Data operations", desc: "Ingestion objectives, red-line probes and dead-letter redrive.", gcp: ["Cloud Run"] },
  { id: "ws-geo", group: "workstations", label: "Geospatial", desc: "Corridors, shared exits, logins and three published lists on one map, with its own agent.", gcp: ["Cloud Run", "BigQuery Graph"] },

  { id: "ag-loop", group: "agents", label: "Workstation agent", desc: "One ADK LoopAgent per workstation: prefetch, draft, verify. Bounded at three iterations and a 30 s deadline.", gcp: ["Vertex AI"], path: "src/eios/assistant/agents.py" },
  { id: "ag-draft", group: "agents", label: "Drafter · Gemini", desc: "An LlmAgent on Gemini (global endpoint) that writes from tool results, with hedged, timed calls.", gcp: ["Vertex AI Gemini"], path: "src/eios/llm_gateway/providers" },
  { id: "ag-asm", group: "agents", label: "Assembler", desc: "A deterministic agent that binds every figure to a value returned this turn, or fails closed.", gcp: [], path: "src/eios/assistant/assembler_agent.py" },
  { id: "ag-armor", group: "agents", label: "Model Armor", desc: "Prompt and response screening once per turn. Deployed services refuse to start without both templates.", gcp: ["Model Armor"], path: "src/eios/assistant/safety.py" },
  { id: "ag-session", group: "agents", label: "Sessions + briefs", desc: "ADK sessions in Firestore behind a write-behind cache; prepared briefs for the top alerts.", gcp: ["Firestore"], path: "src/eios/assistant/sessions.py" },

  { id: "api-web", group: "apis", label: "Next.js web", desc: "The only public surface. Same-origin proxies send its own ID token to the private API.", gcp: ["Cloud Run"], path: "web-prototype/src/app/api" },
  { id: "api-gw", group: "apis", label: "FastAPI gateway", desc: "Verifies Firebase tokens, rate-limits per operator and mounts every domain router.", gcp: ["Cloud Run", "Identity Platform"], path: "src/eios/api/app.py" },
  { id: "api-replay", group: "apis", label: "Evidence replay", desc: "Re-derives each figure of a sealed bundle through the port, as the caller, and compares.", gcp: [], path: "src/eios/evidence" },
  { id: "api-trace", group: "apis", label: "Telemetry", desc: "OpenTelemetry spans per turn and per tool, exported to Cloud Trace (merged, not yet deployed). No prompt text is kept on spans or logs.", gcp: ["Cloud Trace"], path: "src/eios/observability/cloud_trace.py" },

  { id: "on-metrics", group: "ontology", label: "Metric registry", desc: "One versioned definition per metric (ADR-003).", gcp: [], path: "src/eios/ontology/metrics" },
  { id: "on-graph", group: "ontology", label: "Entity graph", desc: "Accounts, devices, payment methods and gateways, with public hubs past degree 100 collapsed (RL-4).", gcp: ["BigQuery Graph"], path: "src/eios/ontology/graph" },
  { id: "on-port", group: "ontology", label: "Governed tool port", desc: "Typed, role-scoped capabilities. Arguments validated, results checked against contract, every call traced. No approve or execute tool exists.", gcp: [], path: "src/eios/ontology/omcp/port" },
  { id: "on-auditor", group: "ontology", label: "Metric auditor", desc: "Any number in an answer must trace to a tool result (RL-1).", gcp: [], path: "src/eios/ontology/auditor" },
  { id: "on-intents", group: "ontology", label: "Action Intents", desc: "Validated, signed, expiring proposals: the only path that can change state.", gcp: [], path: "src/eios/ontology/actions" },

  { id: "d-worlds", group: "data", label: "Seeded worlds", desc: "AML, partner and executive worlds with a planted answer key that only evaluations read.", gcp: [], path: "src/eios/foundry" },
  { id: "d-ref", group: "data", label: "Reference layer", desc: "Overture boundaries, FATF, EU and Basel lists, ICIJ counts and World Bank indicators, each row with source and as-of.", gcp: ["BigQuery", "BigQuery public data"] },
  { id: "d-net", group: "data", label: "IP network intel", desc: "IPinfo Lite plus Tor, cloud and VPN ranges as a hosted snapshot: 14 µs per lookup [MEASURED].", gcp: ["BigQuery"], path: "src/eios/netintel" },
  { id: "d-reg", group: "data", label: "Regulation corpus", desc: "Five regulatory documents, parsed with page spans; the assistant quotes them by sentence.", gcp: ["Agent Search", "Cloud Storage"], path: "src/eios/knowledge" },
  { id: "d-ingest", group: "data", label: "Ingestion", desc: "Events validated against contracts; a breach goes to a dead-letter queue, never dropped.", gcp: ["Pub/Sub"], path: "src/eios/ingestion" },

  { id: "l-triage", group: "logic", label: "Alert triage", desc: "Supervised scorer and queue prioritiser over the raw alert stream.", gcp: [], path: "src/eios/aml/triage_scorer.py" },
  { id: "l-typ", group: "logic", label: "Typologies", desc: "IsolationForest on residual transactions for novel patterns.", gcp: [], path: "src/eios/aml/emerging_typologies.py" },
  { id: "l-hazard", group: "logic", label: "Churn hazard", desc: "Discrete-time logistic hazard, change points and cohorts.", gcp: [], path: "src/eios/churn" },
  { id: "l-causal", group: "logic", label: "Causal SCM", desc: "Edges kept only past placebo and confidence thresholds, otherwise Correlation Only (RL-3).", gcp: [], path: "src/eios/synthesis/scm_fit.py" },
  { id: "l-forecast", group: "logic", label: "Forecast + what-if", desc: "Ridge with leading indicators; shocks attributed to exactly 100%.", gcp: [], path: "src/eios/synthesis" },
  { id: "l-bqg", group: "logic", label: "BigQuery Graph", desc: "Named GQL traversals: account_neighbourhood, exit_ring, country_links. Equal to the local double, median 1.70 s [MEASURED].", gcp: ["BigQuery Graph"], path: "src/eios/graph/queries.py",
    query: "-- exit_ring.users, run through GRAPH_TABLE\nMATCH (g:Gateway)<-[v:LOGGED_IN_VIA]-(a:Account)\nWHERE g.gateway_id = @gateway AND NOT g.hub\nRETURN a.account_id, a.kyc_country, v.sessions" },

  { id: "a-hub", group: "action", label: "Intent hub", desc: "Validates, signs and ledgers every proposed state change.", gcp: [], path: "src/eios/ontology/actions/intent_hub.py" },
  { id: "a-kms", group: "action", label: "Cloud KMS signer", desc: "ECDSA P-256 over each intent and its evidence. Signing and verifying are separate roles.", gcp: ["Cloud KMS"], path: "src/eios/ontology/actions/signer.py" },
  { id: "a-4eyes", group: "action", label: "Four-eyes approval", desc: "The proposer cannot approve. Expired intents can only be discarded.", gcp: ["Firestore"] },
  { id: "a-ledger", group: "action", label: "WORM ledger", desc: "Monotonic sequence and a SHA-256 chain on every approval (RL-5).", gcp: ["Firestore"] },
  { id: "a-evidence", group: "action", label: "Evidence bundles", desc: "Canonical JSON whose id is its SHA-256; a mismatch on read is refused as tampered.", gcp: [] },
];

export interface TraceStep {
  readonly node: string;
  readonly caption: string;
}

export const TRACES: Readonly<Record<"question" | "action", readonly TraceStep[]>> = {
  question: [
    { node: "ws-geo", caption: "An investigator asks the map who uses the shared exit GW-NG-X00." },
    { node: "api-web", caption: "The public web service forwards it with its own ID token." },
    { node: "api-gw", caption: "The private gateway verifies the operator's token and binds the principal." },
    { node: "ag-armor", caption: "Model Armor screens the prompt once for the turn." },
    { node: "ag-loop", caption: "The geospatial agent's loop starts; the selected exit's tool is prefetched." },
    { node: "on-port", caption: "The tool port validates the call and the workstation's allow-list." },
    { node: "l-bqg", caption: "BigQuery Graph runs the named exit_ring traversal." },
    { node: "ag-draft", caption: "Gemini drafts from what the tool returned." },
    { node: "ag-asm", caption: "The assembler binds every figure and map move to this turn's results." },
    { node: "ws-geo", caption: "The answer arrives with citations, and the map moves to the returned objects." },
  ],
  action: [
    { node: "ag-draft", caption: "The agent concludes a withdrawal should be held, and can only propose." },
    { node: "on-intents", caption: "The proposal becomes an Action Intent with the evidence bundle it relied on." },
    { node: "a-hub", caption: "The intent hub validates it against policy." },
    { node: "a-kms", caption: "Cloud KMS signs it. It will expire if nobody acts." },
    { node: "a-4eyes", caption: "A second operator approves. The proposer could not." },
    { node: "a-ledger", caption: "The approval is chained into the write-once ledger." },
    { node: "a-evidence", caption: "The sealed evidence stays replayable against the live engines." },
    { node: "ws-comp", caption: "Compliance can verify the chain end to end." },
  ],
};
