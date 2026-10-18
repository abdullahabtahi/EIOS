import React from "react";
import { ENGAGEMENT } from "./content";

interface Finding {
  readonly found: string;
  readonly built: string;
  readonly href: string;
  readonly capability: string;
}

const FINDINGS: readonly Finding[] = [
  {
    found: "Alerts outnumber analysts, and shared infrastructure fakes connections between strangers.",
    built: "Network science over devices, payment methods and timing that collapses public hubs before it calls anything a ring.",
    href: "#capabilities",
    capability: "Network science",
  },
  {
    found: "Leadership could not tell a cause from a coincidence, so every countermeasure was a guess.",
    built: "A fitted causal graph whose edges must survive refutation, and a what-if that says Correlation Only the moment it leaves the history.",
    href: "#capabilities",
    capability: "Causal inference",
  },
  {
    found: "Money moves through geography, but geography is easy to read as a verdict about people.",
    built: "Map lenses on corridors, shared exits and login countries, published lists as evidence, and a refusal to rank anyone by origin.",
    href: "#geo",
    capability: "Financial geospatial",
  },
  {
    found: "Generic copilots invent numbers and act without authority.",
    built: "One agent per workstation that may cite only what a tool returned in the same turn, and can only propose.",
    href: "#capabilities",
    capability: "Agentic AI",
  },
  {
    found: "A decision nobody can replay is a liability in front of a regulator.",
    built: "Signed, expiring intents, four-eyes approval and a hash-chained ledger that replays the evidence behind every action.",
    href: "#capabilities",
    capability: "Governed action",
  },
];

export function Problem() {
  return (
    <section className="fde-problem" aria-labelledby="fde-problem-title">
      <div className="fde-problem-head" data-reveal>
        <div className="fde-problem-copy">
          <h2 id="fde-problem-title" className="fde-h2">
            Every answer had to survive an auditor. Most tools could not produce one.
          </h2>
          <p>
            The brief came from a regulated financial institution: investigators clearing alerts, partner managers watching
            churn, compliance reviewers, data operations and executives, each on a separate tool. The engagement started with
            the people who would be accountable for an answer, and worked back to the system that could give one.
          </p>
        </div>
        <dl className="fde-engagement">
          {ENGAGEMENT.map((row) => (
            <div key={row.label}>
              <dt>{row.label}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      <table className="fde-findings" data-reveal>
        <caption className="fde-sr">What the field showed, and what was built in response</caption>
        <thead>
          <tr>
            <th scope="col">What the field showed</th>
            <th scope="col">What was built</th>
            <th scope="col">
              <span className="fde-sr">Capability</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {FINDINGS.map((row) => (
            <tr key={row.capability}>
              <th scope="row">{row.found}</th>
              <td>{row.built}</td>
              <td>
                <a href={row.href} className="fde-findings-link">
                  {row.capability} <span aria-hidden="true">→</span>
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
