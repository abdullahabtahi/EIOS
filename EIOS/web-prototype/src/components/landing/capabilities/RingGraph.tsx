"use client";

import React, { useMemo, useState } from "react";
import { HUB, RING_SIZE, RING_SUSPECT, SHARED_DEVICE, SHARED_PAYMENT } from "../data/ring";

const W = 560;
const H = 440;
const RING_C = { x: 210, y: 230 };
const RING_R = 128;
const HUB_P = { x: 452, y: 112 };

/** Deterministic scatter for the hub's other users, so the drawing never shifts between renders. */
function cloud(n: number): Array<{ x: number; y: number }> {
  let seed = 7;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  return Array.from({ length: n }, () => {
    const a = rand() * Math.PI * 2;
    const r = 26 + Math.sqrt(rand()) * 92;
    return { x: HUB_P.x + Math.cos(a) * r * 0.9, y: HUB_P.y + 40 + Math.sin(a) * r * 1.05 };
  });
}

function ringPoints(n: number): Array<{ x: number; y: number }> {
  return Array.from({ length: n }, (_, i) => {
    const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
    return { x: RING_C.x + Math.cos(a) * RING_R, y: RING_C.y + Math.sin(a) * RING_R };
  });
}

export function RingGraph() {
  const [suppressed, setSuppressed] = useState(true);
  const ring = useMemo(() => ringPoints(RING_SIZE), []);
  const others = useMemo(() => cloud(HUB.collapsed), []);
  const device = { x: RING_C.x - 26, y: RING_C.y - 8 };
  const token = { x: RING_C.x + 30, y: RING_C.y + 14 };
  const suspect = ring[0];

  return (
    <figure className="fde-viz" data-suppressed={suppressed}>
      <div className="fde-viz-bar">
        <button
          type="button"
          className="fde-switch"
          aria-pressed={suppressed}
          onClick={() => setSuppressed((s) => !s)}
        >
          <span className="fde-switch-track" aria-hidden="true">
            <span className="fde-switch-thumb" />
          </span>
          Hub suppression (RL-4) {suppressed ? "on" : "off"}
        </button>
        <p className="fde-viz-readout" aria-live="polite">
          {suppressed
            ? `Ring: ${RING_SIZE} accounts on one device and one payment method`
            : `False merge: +${HUB.collapsed} unrelated accounts through one public gateway`}
        </p>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="fde-ring" role="img" aria-label="Case CR84920: 23 accounts linked by a shared device and payment method, and a public gateway that would merge 141 strangers into the ring unless it is collapsed.">
        <g className="fde-ring-cloud">
          {others.map((p, i) => (
            <g key={i}>
              <path d={`M${HUB_P.x} ${HUB_P.y}L${p.x} ${p.y}`} className="fde-ring-cloud-edge" />
              <circle cx={p.x} cy={p.y} r={2.4} className="fde-ring-cloud-node" />
            </g>
          ))}
          <ellipse cx={330} cy={210} rx={262} ry={196} className="fde-ring-false-hull" />
        </g>

        {ring.map((p, i) => (
          <g key={i}>
            <path d={`M${p.x} ${p.y}L${device.x} ${device.y}`} className="fde-ring-edge" />
            <path d={`M${p.x} ${p.y}L${token.x} ${token.y}`} className="fde-ring-edge fde-ring-edge-2" />
          </g>
        ))}
        <circle cx={RING_C.x} cy={RING_C.y} r={RING_R + 22} className="fde-ring-hull" />

        <path d={`M${suspect.x} ${suspect.y}Q${HUB_P.x - 60} ${suspect.y - 10} ${HUB_P.x} ${HUB_P.y}`} className="fde-ring-flow" />

        {ring.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={i === 0 ? 7 : 4.5} className={i === 0 ? "fde-ring-suspect" : "fde-ring-node"} />
        ))}
        <rect x={device.x - 9} y={device.y - 9} width={18} height={18} className="fde-ring-key" transform={`rotate(45 ${device.x} ${device.y})`} />
        <rect x={token.x - 8} y={token.y - 8} width={16} height={16} className="fde-ring-key" />

        <g className="fde-ring-hub">
          <circle cx={HUB_P.x} cy={HUB_P.y} r={suppressed ? 9 : 14} className="fde-ring-hub-node" />
          <path d={`M${HUB_P.x - 6} ${HUB_P.y - 6}L${HUB_P.x + 6} ${HUB_P.y + 6}M${HUB_P.x + 6} ${HUB_P.y - 6}L${HUB_P.x - 6} ${HUB_P.y + 6}`} className="fde-ring-hub-x" />
        </g>

        <text x={suspect.x + 12} y={suspect.y - 6} className="fde-ring-label">{RING_SUSPECT}</text>
        <text x={device.x - 92} y={device.y - 14} className="fde-ring-label fde-ring-label-dim">{SHARED_DEVICE}</text>
        <text x={token.x + 14} y={token.y + 26} className="fde-ring-label fde-ring-label-dim">{SHARED_PAYMENT}</text>
        <text x={HUB_P.x - 8} y={HUB_P.y - 24} className="fde-ring-label" textAnchor="end">
          {HUB.id} · degree {HUB.degree}
        </text>
      </svg>
      <figcaption className="fde-viz-cap">
        Engine output for case {RING_SUSPECT} in the seeded world. Ids are synthetic; degrees and counts are what the graph
        engine returned.
      </figcaption>
    </figure>
  );
}
