import React from "react";

interface Service {
  readonly name: string;
  readonly role: string;
  readonly proof: string | null;
}

/** Services provisioned in EIOS/infra or called from EIOS/src; proofs are [MEASURED] results from the repo docs. */
const SERVICES: readonly Service[] = [
  {
    name: "BigQuery Graph",
    role: "Named GQL traversals behind the map and the rings: account_neighbourhood, exit_ring, country_links. The model never writes a query; it names one from a catalogue.",
    proof: "Equal to the local graph double on every named query; median 1.70 s, first query of a process 5.19 s.",
  },
  {
    name: "BigQuery",
    role: "The warm tier and the reference layer: Overture boundaries from BigQuery public data, FATF, EU and Basel lists, ICIJ counts, World Bank indicators and an IP-network snapshot.",
    proof: "4,167,822 IPinfo networks merged to 2,128,989 ranges and loaded in about 83 s; lookups take 14 µs.",
  },
  {
    name: "Vertex AI · Gemini via Google ADK",
    role: "Each workstation has its own assistant, run every turn as an ADK LoopAgent: a prefetcher, a Gemini drafter and a deterministic assembler, on the global endpoint with hedged calls.",
    proof: "Sealed split, run once: 40 of 42 turns pass, 97.8% of figures supported, p95 10.3 s.",
  },
  {
    name: "Agent Search",
    role: "Regulation retrieval with layout-aware chunks and page spans, so every quoted rule carries its document, page and regulator.",
    proof: null,
  },
  {
    name: "Model Armor",
    role: "Prompt and response screening, once per turn. A deployed service refuses to start without both templates.",
    proof: null,
  },
  {
    name: "Cloud Run",
    role: "A public web service and a private API. The web service calls the API with its own ID token so the operator's token passes through untouched.",
    proof: "The API builds its engines at start-up in about 54 s; one instance is kept warm.",
  },
  {
    name: "Cloud KMS",
    role: "ECDSA P-256 signatures on every Action Intent. Signing and public-key reading are separate roles.",
    proof: null,
  },
  {
    name: "Firestore",
    role: "ADK sessions, approvals and the decision ledger, with transactional appends and jittered retry on one named database.",
    proof: null,
  },
  {
    name: "Pub/Sub",
    role: "The ingestion path: every event checked against its contract, breaches routed to a dead-letter queue.",
    proof: "11 of 11 planted breaches quarantined, no healthy event refused, over 2,818 events in the ingestion replay.",
  },
  {
    name: "Cloud Trace",
    role: "OpenTelemetry spans for every turn and tool call, with no prompt text kept on spans or in logs. Merged; ships with the next deploy.",
    proof: null,
  },
  {
    name: "Identity Platform, Secret Manager, Artifact Registry, Cloud Build",
    role: "Operator sign-in, secrets, and images built by a least-privilege pipeline identity and deployed by digest. CI authenticates through Workload Identity Federation.",
    proof: null,
  },
];

export function GoogleCloud() {
  return (
    <div className="fde-gcloud" data-reveal>
      <h3 className="fde-gcloud-title">What each Google Cloud service does here</h3>
      <dl className="fde-gcloud-list">
        {SERVICES.map((s) => (
          <div key={s.name}>
            <dt>{s.name}</dt>
            <dd>
              {s.role}
              {s.proof && (
                <span className="fde-gcloud-proof">
                  {s.proof} <span className="fde-tag">MEASURED</span>
                </span>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
