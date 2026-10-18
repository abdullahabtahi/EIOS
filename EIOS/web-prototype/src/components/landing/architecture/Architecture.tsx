"use client";

import React, { useEffect, useRef, useState } from "react";
import { GROUPS, NODES, TRACES } from "../data/architecture";
import { useMediaQuery, useReducedMotion } from "../hooks";
import { ArchDiagram } from "./ArchDiagram";
import { GoogleCloud } from "./GoogleCloud";

type Mode = "explore" | "gcp" | "question" | "action";

const MODES: ReadonlyArray<{ id: Mode; label: string }> = [
  { id: "explore", label: "Explore" },
  { id: "gcp", label: "Google Cloud" },
  { id: "question", label: "Trace a question" },
  { id: "action", label: "Trace an action" },
];

const QUESTION_STEPS = TRACES.question.length;
const TOTAL_STEPS = QUESTION_STEPS + TRACES.action.length;

export function Architecture() {
  const [mode, setMode] = useState<Mode>("explore");
  const [selected, setSelected] = useState<string | null>("on-port");
  const [step, setStep] = useState(0);
  const [driven, setDriven] = useState(true);
  const drivenRef = useRef(true);
  /** The visitor took the controls, or handed them back by scrolling to the top of the pinned section. */
  const drive = (on: boolean) => {
    drivenRef.current = on;
    setDriven(on);
  };
  const pinRef = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const wide = useMediaQuery("(min-width: 1101px) and (min-height: 640px)");
  const scrollLinked = wide && !reduced && driven;

  const trace = mode === "explore" || mode === "gcp" ? [] : TRACES[mode];

  useEffect(() => {
    if (!wide || reduced) return;
    let raf = 0;
    const update = () => {
      raf = 0;
      const el = pinRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const travel = rect.height - window.innerHeight;
      const p = travel > 0 ? Math.min(1, Math.max(0, -rect.top / travel)) : 0;
      if (p < 0.02 && !drivenRef.current) {
        drivenRef.current = true;
        setDriven(true);
      }
      if (!drivenRef.current || p > 0.995) return;
      const k = Math.floor((Math.max(0, p - 0.05) / 0.9) * TOTAL_STEPS);
      if (p < 0.05) {
        setMode("explore");
        setStep(0);
      } else if (k < QUESTION_STEPS) {
        setMode("question");
        setStep(k);
      } else {
        setMode("action");
        setStep(Math.min(TOTAL_STEPS - 1, k) - QUESTION_STEPS);
      }
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [wide, reduced]);

  useEffect(() => {
    if (mode === "explore" || mode === "gcp" || scrollLinked) return;
    const steps = TRACES[mode].length;
    const id = window.setInterval(
      () => {
        setStep((s) => (s + 1 < steps ? s + 1 : s));
      },
      reduced ? 300 : 1500,
    );
    return () => window.clearInterval(id);
  }, [mode, reduced, scrollLinked]);

  const trail = trace.slice(0, step + 1).map((t) => t.node);
  const current = trace.length
    ? trace[Math.min(step, trace.length - 1)].node
    : null;
  const focusId = current ?? selected;
  const node = NODES.find((n) => n.id === focusId) ?? null;
  const group = node ? GROUPS.find((g) => g.id === node.group) : null;

  const pickMode = (m: Mode) => {
    drive(false);
    setMode(m);
    setStep(0);
  };

  return (
    <section
      id="architecture"
      className="fde-arch"
      aria-labelledby="fde-arch-title"
    >
      <div className="fde-arch-head" data-reveal>
        <h2 id="fde-arch-title" className="fde-h2">
          One ontology between every model and every decision, built on Google
          Cloud.
        </h2>
        <p className="fde-note">
          Agents and workstations sit above the governed tool port; data,
          engines and the systems that can change state sit below it. Nothing
          crosses the middle except through a typed, role-scoped, traced call.
          Select any component, or trace a request end to end.
        </p>
      </div>

      <div
        ref={pinRef}
        className={`fde-arch-pin${wide && !reduced ? " is-pinned" : ""}`}
      >
        <div className="fde-arch-pin-sticky">
          <div className="fde-arch-body">
            <div className="fde-arch-stage">
              <div
                className="fde-seg"
                role="group"
                aria-label="Architecture view"
              >
                {MODES.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    aria-pressed={mode === m.id}
                    onClick={() => pickMode(m.id)}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              <ArchDiagram
                selected={
                  mode === "explore" || mode === "gcp" ? selected : null
                }
                gcpLens={mode === "gcp"}
                trail={trail}
                current={current}
                onSelect={(id) => {
                  drive(false);
                  if (mode !== "gcp") setMode("explore");
                  setSelected(id);
                }}
              />
              <ul
                className="fde-arch-list"
                aria-label="Architecture components by layer"
              >
                {GROUPS.map((g) => (
                  <li key={g.id}>
                    <p className="fde-arch-list-group">{g.label}</p>
                    <div className="fde-arch-list-chips">
                      {NODES.filter((n) => n.group === g.id).map((n) => (
                        <button
                          key={n.id}
                          type="button"
                          aria-pressed={focusId === n.id}
                          className={`${n.gcp.length ? "has-gcp" : ""}${trail.includes(n.id) ? " is-trail" : ""}`}
                          onClick={() => {
                            drive(false);
                            if (mode !== "gcp") setMode("explore");
                            setSelected(n.id);
                          }}
                        >
                          {n.label}
                        </button>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
              <p className="fde-arch-key">
                <span className="fde-arch-key-gcp" aria-hidden="true" /> runs on
                a Google Cloud service
              </p>
            </div>

            <aside className="fde-arch-panel" aria-live="polite">
              {trace.length > 0 && (
                <div className="fde-arch-trace">
                  <p className="fde-arch-step">
                    Step {Math.min(step, trace.length - 1) + 1} of{" "}
                    {trace.length}
                  </p>
                  <p className="fde-arch-caption">
                    {trace[Math.min(step, trace.length - 1)].caption}
                  </p>
                  <div className="fde-arch-trace-ctl">
                    <button
                      type="button"
                      className="fde-chipbtn"
                      onClick={() => {
                        drive(false);
                        setStep((s) => Math.max(0, s - 1));
                      }}
                      disabled={step === 0}
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      className="fde-chipbtn"
                      onClick={() => {
                        drive(false);
                        setStep((s) => Math.min(trace.length - 1, s + 1));
                      }}
                      disabled={step >= trace.length - 1}
                    >
                      Next
                    </button>
                    <button
                      type="button"
                      className="fde-chipbtn"
                      onClick={() => {
                        drive(false);
                        setStep(0);
                      }}
                    >
                      Replay
                    </button>
                  </div>
                </div>
              )}
              {node && group && (
                <div className="fde-arch-detail">
                  <h3 className="fde-arch-name">{node.label}</h3>
                  <p className="fde-arch-desc">{node.desc}</p>
                  {node.gcp.length > 0 && (
                    <p className="fde-cap-runs">
                      <span>Google Cloud</span>
                      {node.gcp.map((g) => (
                        <span key={g} className="fde-gcp">
                          {g}
                        </span>
                      ))}
                    </p>
                  )}
                  {node.query && (
                    <pre className="fde-arch-query">{node.query}</pre>
                  )}
                  {node.path && (
                    <p className="fde-arch-path">EIOS/{node.path}</p>
                  )}
                </div>
              )}
            </aside>
          </div>
          {scrollLinked && (
            <p className="fde-arch-hint">
              Scroll to trace a question, then an action. Use the controls to
              take over.
            </p>
          )}
        </div>
      </div>

      <GoogleCloud />
    </section>
  );
}
