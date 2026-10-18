"use client";

import React, { useRef, useState } from "react";
import { AgentTrace } from "./AgentTrace";
import { CausalWhatIf } from "./CausalWhatIf";
import { GovernedAction } from "./GovernedAction";
import { RingGraph } from "./RingGraph";

interface Capability {
  readonly id: string;
  readonly tab: string;
  readonly title: string;
  readonly body: string;
  readonly under: readonly string[];
  readonly runsOn: readonly string[];
  readonly Figure: () => React.JSX.Element;
}

const CAPABILITIES: readonly Capability[] = [
  {
    id: "network",
    tab: "Network science",
    title: "Find the ring, not the router.",
    body:
      "Accounts are linked through shared devices, payment methods and matched timing. A public gateway touches hundreds of strangers; left in the graph, it fuses them into one false ring. Hubs past degree 100 are collapsed before anything is called a ring.",
    under: ["Bipartite graphs over payments, devices and IPs", "Degree-penalised hub suppression (RL-4)", "Named GQL traversals on BigQuery Graph"],
    runsOn: ["BigQuery Graph", "BigQuery"],
    Figure: RingGraph,
  },
  {
    id: "causal",
    tab: "Causal inference",
    title: "A cause is a claim the data has to survive.",
    body:
      "The executive engine fits a structural causal model and keeps an edge only when placebo, random-common-cause and subset refuters pass. Drag the shock: inside the history the what-if is causal; past it, the engine says Correlation Only instead of guessing.",
    under: ["Standardised ridge with Frisch-Waugh adjustment", "Doubly robust AIPW effect estimates", "Backtested forecast, 90% interval held 87% out of sample"],
    runsOn: ["Cloud Run"],
    Figure: CausalWhatIf,
  },
  {
    id: "agents",
    tab: "Agentic AI",
    title: "The model writes the sentence. A tool supplies the number.",
    body:
      "One Google ADK agent per workstation works only through a typed, role-scoped tool port. A deterministic assembler binds every figure to a value a tool returned in the same turn; anything else is sent back once, then the turn fails closed.",
    under: ["ADK LoopAgent: prefetch, drafter, assembler", "Regulation quoted by sentence from Agent Search", "Prompt and reply screened by Model Armor"],
    runsOn: ["Vertex AI Gemini", "Agent Search", "Model Armor", "Firestore"],
    Figure: AgentTrace,
  },
  {
    id: "governance",
    tab: "Governed action",
    title: "Agents propose. Two people decide. The ledger remembers.",
    body:
      "No tool can approve or execute. A proposal becomes an Action Intent that Cloud KMS signs and that expires; a second operator must approve it, and the approval is chained into a write-once ledger with the evidence it relied on.",
    under: ["ECDSA P-256 signatures on every intent", "Four-eyes rule enforced in the hub", "SHA-256 chained, monotonic ledger with evidence replay"],
    runsOn: ["Cloud KMS", "Firestore"],
    Figure: GovernedAction,
  },
];

export function Capabilities() {
  const [active, setActive] = useState(0);
  const tabs = useRef<Array<HTMLButtonElement | null>>([]);
  const cap = CAPABILITIES[active];

  const onKey = (e: React.KeyboardEvent, i: number) => {
    const dir = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!dir) return;
    e.preventDefault();
    const next = (i + dir + CAPABILITIES.length) % CAPABILITIES.length;
    setActive(next);
    tabs.current[next]?.focus();
  };

  return (
    <section id="capabilities" className="fde-caps" aria-labelledby="fde-caps-title">
      <div className="fde-caps-head" data-reveal>
        <h2 id="fde-caps-title" className="fde-h2">
          Four capabilities, each one you can push on.
        </h2>
        <p className="fde-note">
          Every figure below is drawn from the running engines or from recorded live turns. Try to break them.
        </p>
      </div>

      <div className="fde-tabs" role="tablist" aria-label="Capabilities">
        {CAPABILITIES.map((c, i) => (
          <button
            key={c.id}
            ref={(el) => {
              tabs.current[i] = el;
            }}
            role="tab"
            id={`fde-tab-${c.id}`}
            aria-selected={i === active}
            aria-controls={`fde-panel-${c.id}`}
            tabIndex={i === active ? 0 : -1}
            className="fde-tab"
            onClick={() => setActive(i)}
            onKeyDown={(e) => onKey(e, i)}
          >
            <span className="fde-tab-name">{c.tab}</span>
          </button>
        ))}
      </div>

      <div
        role="tabpanel"
        id={`fde-panel-${cap.id}`}
        aria-labelledby={`fde-tab-${cap.id}`}
        className="fde-cap"
        key={cap.id}
      >
        <div className="fde-cap-copy">
          <h3 className="fde-cap-title">{cap.title}</h3>
          <p className="fde-cap-body">{cap.body}</p>
          <ul className="fde-cap-under">
            {cap.under.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
          <p className="fde-cap-runs">
            <span>Runs on</span>
            {cap.runsOn.map((r) => (
              <span key={r} className="fde-gcp">
                {r}
              </span>
            ))}
          </p>
        </div>
        <cap.Figure />
      </div>
    </section>
  );
}
