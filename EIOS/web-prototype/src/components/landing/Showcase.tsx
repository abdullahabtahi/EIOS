"use client";

import Link from "next/link";
import React, { useState } from "react";
import { landingAsset, landingSrcSet } from "./assets";
import { APP_HOME_HREF } from "@/components/cockpit/shell/app-nav-items";

interface Callout {
  readonly x: number;
  readonly y: number;
  readonly label: string;
  readonly body: string;
}

interface Screen {
  readonly id: string;
  readonly tab: string;
  readonly stem: string;
  readonly alt: string;
  readonly callouts: readonly Callout[];
}

/** Screenshots of the real workstations (production build, local engine gateway, synthetic client data), 2026-10-18. */
const SCREENS: readonly Screen[] = [
  {
    id: "aml",
    tab: "AML investigator",
    stem: "workstation-aml",
    alt: "The AML investigator workstation: triage queue, evidence dossier, network graph, entity inspector and SAR composer.",
    callouts: [
      { x: 12, y: 24, label: "Triage", body: "Rings and alerts ranked by the engine's score, filterable by severity." },
      { x: 36, y: 30, label: "Evidence dossier", body: "Why the case was raised, every figure with a citation and its geography flagged." },
      { x: 63, y: 50, label: "Network graph", body: "The ring around CR84920 with public hubs past degree 100 collapsed." },
      { x: 87, y: 40, label: "Entity inspector", body: "Centrality, 30-day velocity and the counterparties, by volume." },
      { x: 72, y: 87, label: "SAR composer", body: "A near-final narrative drafted from the same evidence." },
      { x: 13, y: 97, label: "Governed action shelf", body: "Staged and expired intents; nothing executes without a second approver." },
    ],
  },
  {
    id: "exec",
    tab: "Executive",
    stem: "workstation-exec",
    alt: "The executive workstation: morning briefing, 28-day revenue projection and the fitted causal graph with refuter verdicts.",
    callouts: [
      { x: 18, y: 32, label: "Morning briefing", body: "Four horizons, each figure computed by an engine and cited." },
      { x: 50, y: 30, label: "Projection", body: "28 days ahead with a backtested 90% interval." },
      { x: 62, y: 72, label: "Causal graph", body: "Fitted from two years of daily history; the spread link reads correlation only." },
      { x: 70, y: 94, label: "Refuter verdicts", body: "Effect, stability and placebo p-value for every link." },
    ],
  },
];

/** Widths of the pre-built `-1200` and `-1800` variants beside the 2400 original; the shot is at most about 1100 css px wide. */
const SHOT_WIDTHS = [1200, 1800] as const;
const SHOT_SIZES = "(max-width: 1200px) 100vw, 1100px";

export function Showcase() {
  const [idx, setIdx] = useState(0);
  const [hot, setHot] = useState<number | null>(null);
  const screen = SCREENS[idx];

  return (
    <section id="product" className="fde-show" aria-labelledby="fde-show-title">
      <div className="fde-show-head" data-reveal>
        <h2 id="fde-show-title" className="fde-h2">
          What an analyst actually works in.
        </h2>
        <div className="fde-seg" role="group" aria-label="Workstation">
          {SCREENS.map((s, i) => (
            <button
              key={s.id}
              type="button"
              aria-pressed={i === idx}
              onClick={() => {
                setIdx(i);
                setHot(null);
              }}
            >
              {s.tab}
            </button>
          ))}
        </div>
      </div>

      <div className="fde-show-body">
        <figure className="fde-shot" key={screen.id}>
          {/* eslint-disable-next-line @next/next/no-img-element -- static capture, fixed intrinsic size */}
          <img
            src={landingAsset(`${screen.stem}.webp`)}
            srcSet={landingSrcSet(screen.stem, SHOT_WIDTHS, 2400)}
            sizes={SHOT_SIZES}
            alt={screen.alt}
            width={2400}
            height={1500}
            loading="lazy"
            decoding="async"
          />
          {screen.callouts.map((c, i) => (
            <button
              key={c.label}
              type="button"
              className={`fde-pin-mark${hot === i ? " is-hot" : ""}`}
              style={{ left: `${c.x}%`, top: `${c.y}%` }}
              aria-label={`${i + 1}. ${c.label}`}
              onMouseEnter={() => setHot(i)}
              onFocus={() => setHot(i)}
              onMouseLeave={() => setHot(null)}
              onBlur={() => setHot(null)}
            >
              {i + 1}
            </button>
          ))}
          <figcaption className="fde-viz-cap">
            Screenshot of the {screen.tab.toLowerCase()} workstation from the production build against the engine gateway.
            Client data is synthetic.
          </figcaption>
        </figure>

        <ol className="fde-show-list">
          {screen.callouts.map((c, i) => (
            <li
              key={c.label}
              className={hot === i ? "is-hot" : undefined}
              onMouseEnter={() => setHot(i)}
              onMouseLeave={() => setHot(null)}
            >
              <span className="fde-show-n">{i + 1}</span>
              <div>
                <p className="fde-show-label">{c.label}</p>
                <p className="fde-show-body-text">{c.body}</p>
              </div>
            </li>
          ))}
          <li className="fde-show-cta">
            <Link href={APP_HOME_HREF} className="fde-findings-link">
              Open the workstation <span aria-hidden="true">→</span>
            </Link>
          </li>
        </ol>
      </div>
    </section>
  );
}
