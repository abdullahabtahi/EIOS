import React from "react";
import { RED_LINES } from "./content";

export function RedLines() {
  return (
    <section id="red-lines" className="fde-redlines" aria-labelledby="fde-redlines-title">
      <div className="fde-redlines-head" data-reveal>
        <h2 id="fde-redlines-title" className="fde-h2">
          Seven rules the system is not allowed to break.
        </h2>
        <p className="fde-note">
          They are checked as tests and, where a probe is safe, against the running system. Two cannot be probed live without
          writing state or faking an outage, and the operations board says so instead of showing green.
        </p>
      </div>
      <ol className="fde-rules" data-reveal>
        {RED_LINES.map((line) => (
          <li key={line.id}>
            <span className="fde-rule-id">{line.id}</span>
            <div>
              <p className="fde-rule-text">{line.rule}</p>
              <p className="fde-rule-how">{line.enforced}</p>
            </div>
            <span className={`fde-status${line.status === "NOT MEASURED" ? " is-open" : ""}`}>{line.status}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
