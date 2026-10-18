"use client";

import React, { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../hooks";

interface Step {
  readonly key: string;
  readonly name: string;
  readonly who: string;
  readonly detail: string;
  readonly code?: string;
}

/** One recorded turn from the 2026-10-18 live run (case aml_dossier_discrepancy), walked through the ADK loop. */
const STEPS: readonly Step[] = [
  {
    key: "ask",
    name: "Question",
    who: "AML workstation · verified identity",
    detail: "The operator's Firebase token becomes a principal bound into every tool. The model never holds an identity.",
    code: "What is the turnover discrepancy for account CR84920?",
  },
  {
    key: "screen",
    name: "Screen",
    who: "Model Armor",
    detail: "The prompt is screened once per turn and the reply after the model. A block, or a failed screening, stops the turn.",
  },
  {
    key: "prefetch",
    name: "Prefetch",
    who: "Platform agent (no LLM)",
    detail: "When the tool is obvious, the platform runs it before the model is called, through the governed tool port: arguments validated, role allow-list checked, result traced.",
    code: "get_aml_dossier(entity_id=\"CR84920\")  →  discrepancy_multiplier: 16.0  (unit: multiplier)",
  },
  {
    key: "draft",
    name: "Draft",
    who: "Gemini through ADK (LlmAgent)",
    detail: "The drafter writes plain sentences and figures. It may only use what tools returned in this turn.",
    code: "Account CR84920 has a turnover discrepancy multiplier of 16.",
  },
  {
    key: "assemble",
    name: "Verify",
    who: "Assembler (deterministic)",
    detail: "Every figure is matched to a returned value at the precision and in the unit written. An unmatched figure sends the draft back once, then the turn fails closed.",
    code: "\"16\" (characters 57-59) matches tool call 0, discrepancy_multiplier = 16.0: bound and cited",
  },
  {
    key: "answer",
    name: "Answer",
    who: "Workstation",
    detail: "The operator sees the assembler's answer with its citation and as-of time. The evidence bundle is sealed by SHA-256 and can be replayed later.",
    code: "Account CR84920 has a turnover discrepancy multiplier of 16.   as of 2026-10-14 08:00 UTC",
  },
];

export function AgentTrace() {
  const [active, setActive] = useState(0);
  const [inject, setInject] = useState(false);
  const [playing, setPlaying] = useState(false);
  const reduced = useReducedMotion();
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!playing) return;
    timer.current = window.setInterval(() => {
      setActive((a) => {
        if (a >= STEPS.length - 1) {
          setPlaying(false);
          return a;
        }
        return a + 1;
      });
    }, reduced ? 400 : 1600);
    return () => window.clearInterval(timer.current);
  }, [playing, reduced]);

  const step = STEPS[active];
  const rejected = inject && (step.key === "assemble" || step.key === "answer");

  return (
    <figure className="fde-viz">
      <div className="fde-viz-bar">
        <button
          type="button"
          className="fde-chipbtn"
          onClick={() => {
            setActive(0);
            setPlaying(true);
          }}
        >
          Play the turn
        </button>
        <button type="button" className="fde-switch" aria-pressed={inject} onClick={() => setInject((v) => !v)}>
          <span className="fde-switch-track" aria-hidden="true">
            <span className="fde-switch-thumb" />
          </span>
          Slip in a figure no tool returned
        </button>
      </div>

      <ol className="fde-trace" aria-label="Steps of one assistant turn">
        {STEPS.map((s, i) => (
          <li key={s.key}>
            <button
              type="button"
              className={`fde-trace-step${i === active ? " is-active" : ""}${i < active ? " is-done" : ""}${
                inject && s.key === "assemble" ? " is-reject" : ""
              }`}
              aria-current={i === active ? "step" : undefined}
              onClick={() => {
                setPlaying(false);
                setActive(i);
              }}
            >
              <span className="fde-trace-n">{String(i + 1).padStart(2, "0")}</span>
              <span className="fde-trace-name">{s.name}</span>
            </button>
          </li>
        ))}
      </ol>

      <div className="fde-trace-panel" aria-live="polite">
        <p className="fde-trace-who">Runs in: {step.who}</p>
        <p className="fde-trace-detail">{step.detail}</p>
        {step.code && !rejected && <pre className="fde-trace-code">{inject && step.key === "draft" ? `${step.code} It also moved $2.4M last week.` : step.code}</pre>}
        {rejected && step.key === "assemble" && (
          <pre className="fde-trace-code is-reject">
            {"$2.4M matches no value a tool returned: rejected.\nThe draft goes back once with the reason; a second miss fails closed."}
          </pre>
        )}
        {rejected && step.key === "answer" && (
          <pre className="fde-trace-code">{"Account CR84920 has a turnover discrepancy multiplier of 16.\n(the unsupported sentence never reaches the operator)"}</pre>
        )}
      </div>
      <figcaption className="fde-viz-cap">
        Question, tool and answer are from a recorded live turn (2026-10-18 evaluation run). The slipped-in figure illustrates the
        assembler&apos;s rule; it is not from that run.
      </figcaption>
    </figure>
  );
}
