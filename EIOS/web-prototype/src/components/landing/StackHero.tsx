"use client";

import React, { useState } from "react";
import { LAYERS } from "./content";
import { SLAB_CY, StackSvg, VIEW_H } from "./StackSvg";

const BAND = 118;

function bandStyle(k: number): React.CSSProperties {
  const cy = SLAB_CY[k];
  return {
    top: `${((cy - BAND / 2) / VIEW_H) * 100}%`,
    height: `${(BAND / VIEW_H) * 100}%`,
  };
}

export function StackHero() {
  const [active, setActive] = useState<number | null>(null);

  return (
    <section className="fde-hero" aria-labelledby="fde-title">
      <div className="fde-hero-copy">
        <p className="fde-crumb">
          <span className="fde-crumb-pill">Case study</span>
          <span className="fde-crumb-arrow" aria-hidden="true" />
          <span>Financial services</span>
        </p>
        <h1 id="fde-title" className="fde-display">
          A governed intelligence layer, built in the field.
        </h1>
        <p className="fde-lede">
          A forward-deployed engineering case study. An AML, partner and executive intelligence system, taken from proof of
          concept to a production-shaped deployment, with every figure traced and every action signed.
        </p>
        <div className="fde-hero-foot">
          <a href="#system" className="fde-scroll-cue">
            Read the case study <span aria-hidden="true">↓</span>
          </a>
          <p className="fde-entry">
            <span>Entry for</span>
            {/* eslint-disable-next-line @next/next/no-img-element -- small static logo */}
            <img src="/landing/ai-builder-cup.webp" alt="AI Builder Cup by Google Cloud and Hack2skill" width={430} height={222} />
          </p>
        </div>
      </div>

      <div className="fde-diagram" onMouseLeave={() => setActive(null)}>
        <div className="fde-stack">
          <StackSvg active={active} />
        </div>

        <ol className="fde-legend" aria-label="The five layers, from the bottom up">
          {LAYERS.map((layer, k) => (
            <li
              key={layer.n}
              className={`fde-band${active === k ? " is-active" : ""}`}
              style={bandStyle(k)}
              onMouseEnter={() => setActive(k)}
              onFocus={() => setActive(k)}
              onBlur={() => setActive(null)}
              tabIndex={0}
            >
              <span className="fde-band-n">{String(layer.n).padStart(2, "0")}</span>
              <div className="fde-band-body">
                <p className="fde-band-name">{layer.name}</p>
                <ul>
                  {layer.legend.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
