"use client";

import React, { useState } from "react";
import { COVERAGE, GEO_AS_OF, HUBS_SUPPRESSED } from "../data/geo";
import { GEO_TURNS } from "../data/turns";
import { GeoMap } from "./GeoMap";
import type { Basis, Lens } from "./geoLayers";

const LENSES: ReadonlyArray<{ id: Lens; label: string }> = [
  { id: "corridors", label: "Corridors" },
  { id: "exits", label: "Shared exits" },
  { id: "jurisdictions", label: "Jurisdictions" },
];

const BASES: ReadonlyArray<{ id: Basis; label: string }> = [
  { id: "fatf", label: "FATF" },
  { id: "eu", label: "EU list" },
  { id: "basel", label: "Basel AML" },
];

const TOOL_LABEL: Readonly<Record<string, string>> = {
  get_geo_overview: "geo.overview",
  get_shared_exit: "geo.exit · BigQuery Graph",
  get_corridor: "geo.corridor",
  get_jurisdiction: "geo.jurisdiction",
  get_list_change_impact: "geo.list_change",
  get_geo_account: "geo.account",
  propose_hold: "actions.propose_hold",
};

const LEGEND: Readonly<Record<Lens, ReadonlyArray<{ cls: string; label: string }>>> = {
  corridors: [
    { cls: "is-low", label: "Low-tier corridor" },
    { cls: "is-mid", label: "Medium" },
    { cls: "is-high", label: "High" },
  ],
  exits: [
    { cls: "is-high", label: "Shared foreign exit" },
    { cls: "is-mid", label: "Home country of its users" },
  ],
  jurisdictions: [],
};

const BASIS_LEGEND: Readonly<Record<Basis, ReadonlyArray<{ cls: string; label: string }>>> = {
  fatf: [
    { cls: "is-high", label: "FATF call for action, or increased monitoring (lighter)" },
    { cls: "is-low", label: "Not listed" },
  ],
  eu: [
    { cls: "is-mid", label: "On the EU high-risk third-country list" },
    { cls: "is-low", label: "Not listed" },
  ],
  basel: [
    { cls: "is-high", label: "Basel AML Index higher band, medium lighter" },
    { cls: "is-low", label: "Lower band" },
  ],
};

export function GeoSection() {
  const [lens, setLens] = useState<Lens>("corridors");
  const [basis, setBasis] = useState<Basis>("fatf");
  const [turnIdx, setTurnIdx] = useState<number | null>(null);
  const turn = turnIdx == null ? null : GEO_TURNS[turnIdx];

  return (
    <section id="geo" className="fde-geo" aria-labelledby="fde-geo-title">
      <div className="fde-interlude">
        <picture>
          <source media="(max-width: 900px)" srcSet="/landing/strait-1200.webp" />
          <img src="/landing/strait-2400.webp" alt="" width={2400} height={1200} loading="lazy" decoding="async" />
        </picture>
        <div className="fde-interlude-copy" data-reveal>
          <h2 id="fde-geo-title" className="fde-interlude-title">
            Money moves through geography. Geography is evidence, never a verdict.
          </h2>
          <p className="fde-interlude-credit">Generated image, not a satellite photograph.</p>
        </div>
      </div>

      <div className="fde-geo-body">
        <div className="fde-geo-panel">
          <p className="fde-geo-lede">
            The sixth workstation reads the book through four lenses and three published lists. Its own Gemini agent answers
            questions and moves the map, but only to objects a tool returned in the same turn.
          </p>

          <div className="fde-seg" role="group" aria-label="Map lens">
            {LENSES.map((l) => (
              <button key={l.id} type="button" aria-pressed={lens === l.id} onClick={() => setLens(l.id)}>
                {l.label}
              </button>
            ))}
          </div>
          {lens === "jurisdictions" && (
            <div className="fde-seg fde-seg-sub" role="group" aria-label="List basis">
              {BASES.map((b) => (
                <button key={b.id} type="button" aria-pressed={basis === b.id} onClick={() => setBasis(b.id)}>
                  {b.label}
                </button>
              ))}
            </div>
          )}

          <h3 className="fde-geo-ask">Replay a recorded turn of the map&apos;s agent</h3>
          <ul className="fde-turns">
            {GEO_TURNS.map((t, i) => (
              <li key={t.id}>
                <button type="button" aria-pressed={turnIdx === i} onClick={() => setTurnIdx(turnIdx === i ? null : i)}>
                  {t.question}
                </button>
              </li>
            ))}
          </ul>

          <div className="fde-turn" aria-live="polite">
            {turn ? (
              <>
                <p className="fde-turn-tools">
                  {turn.tools.length ? turn.tools.map((t) => TOOL_LABEL[t] ?? t).join("  ·  ") : "No tool called: refused before the model ran"}
                </p>
                <p className="fde-turn-answer">{turn.answer}</p>
              </>
            ) : (
              <p className="fde-turn-empty">Pick a question to replay the agent&apos;s answer and its map move.</p>
            )}
          </div>
        </div>

        <div className="fde-geo-map">
          <GeoMap lens={lens} basis={basis} focus={turn?.focus ?? null} />
          <ul className="fde-map-legend" aria-label="Legend">
            {(lens === "jurisdictions" ? BASIS_LEGEND[basis] : LEGEND[lens]).map((l) => (
              <li key={l.label}>
                <span className={`fde-key ${l.cls}`} aria-hidden="true" />
                {l.label}
              </li>
            ))}
          </ul>
          <p className="fde-map-sources">
            Flows: geo engine over the seeded book, {COVERAGE.clients.toLocaleString("en-US")} accounts, {HUBS_SUPPRESSED} hub
            suppressed, as of {GEO_AS_OF.slice(0, 10)}. Lists: FATF (June 2026), EU Delegated Regulation 2016/1675 as amended,
            Basel AML Index 2025. Centroids: Overture Maps. Outlines: Natural Earth.
          </p>
        </div>
      </div>
    </section>
  );
}
