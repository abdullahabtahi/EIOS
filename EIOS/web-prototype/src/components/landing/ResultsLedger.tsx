import React from "react";
import { RESULTS } from "./content";
import { RESULT_CHARTS } from "./data/charts";
import { MiniChart } from "./MiniChart";

const KIND_LABEL = { pass: "Held", miss: "Missed", caveat: "Held, with a caveat" } as const;

export function ResultsLedger() {
  const held = RESULTS.filter((r) => r.kind === "pass").length;
  const caveat = RESULTS.filter((r) => r.kind === "caveat").length;
  const missed = RESULTS.filter((r) => r.kind === "miss").length;
  return (
    <section id="results" className="fde-results" aria-labelledby="fde-results-title">
      <div className="fde-results-head" data-reveal>
        <h2 id="fde-results-title" className="fde-h2">
          {held} held, {caveat} held with a caveat, {missed} missed.
        </h2>
        <p className="fde-note">
          Every row is a result our own harness produced against what the synthetic worlds planted, not production traffic.
          The first live run found a bug in our own grader, so the judge was fixed and frozen before the sealed split ran once.
        </p>
      </div>
      <ol className="fde-ledger" aria-label="Measured results, with the bar each was held to">
        {RESULTS.map((row) => (
          <li key={row.what} data-kind={row.kind} data-reveal>
            <div className="fde-ledger-what">
              <h3>{row.what}</h3>
              <span className="fde-kind">{KIND_LABEL[row.kind]}</span>
            </div>
            <div className="fde-ledger-result">
              <p>
                {row.result} <span className="fde-tag">MEASURED</span>
              </p>
              {(RESULT_CHARTS[row.what] ?? []).map((c, i) => (
                <MiniChart key={i} chart={c} />
              ))}
            </div>
            <p className="fde-ledger-against">{row.against}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
