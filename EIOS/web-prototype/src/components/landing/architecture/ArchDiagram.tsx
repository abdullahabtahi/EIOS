"use client";

import React from "react";
import { GROUPS, type ArchNode } from "../data/architecture";
import { CHIP, PLACED, SLABS, VIEW, WIRES, hop, slabSide, slabTop } from "./archLayout";

export interface ArchDiagramProps {
  readonly selected: string | null;
  readonly trail: readonly string[];
  readonly current: string | null;
  readonly onSelect: (id: string) => void;
  readonly gcpLens?: boolean;
}

function Chip({ node, state, onSelect, gcpLens }: { node: ArchNode; state: string; onSelect: (id: string) => void; gcpLens: boolean }) {
  const p = PLACED[node.id];
  return (
    <g
      className={`fde-arch-chip ${state}`}
      transform={`translate(${p.x - CHIP.w / 2} ${p.y - CHIP.h / 2})`}
      role="button"
      tabIndex={0}
      aria-label={`${node.label}${node.gcp.length ? `, runs on ${node.gcp.join(", ")}` : ""}`}
      aria-pressed={state.includes("is-selected")}
      onClick={() => onSelect(node.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(node.id);
        }
      }}
    >
      <rect width={CHIP.w} height={CHIP.h} rx={2} />
      {node.gcp.length > 0 && <rect x={0} y={0} width={3} height={CHIP.h} className="fde-arch-gcp" />}
      <text x={12} y={CHIP.h / 2 + 5}>{gcpLens && node.gcp.length ? node.gcp[0] : node.label}</text>
    </g>
  );
}

export function ArchDiagram({ selected, trail, current, onSelect, gcpLens = false }: ArchDiagramProps) {
  const selectedGroup = selected ? PLACED[selected]?.node.group : null;
  const trailGroups = new Set(trail.map((id) => PLACED[id]?.node.group));
  const hops = trail.slice(1).map((id, i) => ({ key: `${trail[i]}-${id}-${i}`, d: hop(PLACED[trail[i]], PLACED[id]) }));

  return (
    <svg viewBox={`0 0 ${VIEW.w} ${VIEW.h}`} className="fde-arch-svg" role="group" aria-label="EIOS architecture: workstations, agents and APIs above the ontology; data, engines and systems of action below.">
      {WIRES.map((w) => (
        <path
          key={w.id}
          d={w.d}
          className={`fde-arch-wire${w.group === selectedGroup || trailGroups.has(w.group) ? " is-lit" : ""}`}
        />
      ))}

      {GROUPS.map((g) => {
        const s = SLABS[g.id];
        const lit = g.id === selectedGroup || trailGroups.has(g.id);
        const labelY = g.tier === "top" ? s.cy - 150 : g.tier === "bottom" ? s.cy + s.hh + 40 : s.cy + s.hh + 42;
        return (
          <g key={g.id} className={`fde-arch-slab${lit ? " is-lit" : ""}`}>
            <path d={slabSide(s)} className="fde-arch-side" />
            <path d={slabTop(s)} className="fde-arch-top" />
            <text x={s.cx} y={labelY} textAnchor="middle" className="fde-arch-label">
              {g.label.toUpperCase()}
            </text>
          </g>
        );
      })}

      {Object.values(PLACED).map(({ node }) => {
        const state = [
          node.id === selected ? "is-selected" : "",
          node.id === current ? "is-current" : "",
          trail.includes(node.id) ? "is-trail" : "",
          gcpLens ? (node.gcp.length ? "is-gcp" : "is-dim") : "",
        ]
          .filter(Boolean)
          .join(" ");
        return <Chip key={node.id} node={node} state={state} onSelect={onSelect} gcpLens={gcpLens} />;
      })}

      {hops.map((h) => (
        <path key={h.key} d={h.d} className="fde-arch-hop" />
      ))}
    </svg>
  );
}
