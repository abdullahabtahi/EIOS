"use client";

import React, { useMemo, useState } from "react";
import {
  HUB,
  RING_SIZE,
  RING_SUSPECT,
  SHARED_DEVICE,
  SHARED_PAYMENT,
} from "../data/ring";

const W = 820;
const H = 500;
const SUSPECT = 4;

/** The ring is drawn once in its own coordinates; the hub's burst arrives beside it and the ring shrinks to make room. */
const DEVICE = { x: 150, y: 250 };
const PAYMENT = { x: 650, y: 250 };
const SCALE_OFF = 0.46;
const SHIFT_OFF = { x: 10, y: 190 };
const HUB_ON = { x: 712, y: 66 };
const HUB_OFF = { x: 600, y: 250 };

type Pt = { x: number; y: number };

function accountPoints(n: number): Pt[] {
  return Array.from({ length: n }, (_, i) => ({
    x: 400 + 26 * Math.sin((Math.PI * i) / (n - 1)),
    y: 70 + (i * 360) / (n - 1),
  }));
}

/** Golden-angle spiral: a deterministic, even burst for the hub's other users. */
function burst(n: number): Pt[] {
  return Array.from({ length: n }, (_, i) => {
    const r = 14 + 14.2 * Math.sqrt(i);
    const a = i * 2.399963;
    return { x: HUB_OFF.x + Math.cos(a) * r, y: HUB_OFF.y + Math.sin(a) * r };
  });
}

const toGlobal = (p: Pt, off: boolean): Pt =>
  off
    ? { x: SHIFT_OFF.x + p.x * SCALE_OFF, y: SHIFT_OFF.y + p.y * SCALE_OFF }
    : p;

export function RingGraph() {
  const [suppressed, setSuppressed] = useState(true);
  const accounts = useMemo(() => accountPoints(RING_SIZE), []);
  const others = useMemo(() => burst(HUB.collapsed), []);
  const off = !suppressed;
  const suspect = accounts[SUSPECT];

  const at = (p: Pt, dx = 0, dy = 0) => {
    const g = toGlobal(p, off);
    return { x: g.x + dx, y: g.y + dy };
  };
  const dev = at(DEVICE, 0, off ? 20 : 34);
  const pay = at(PAYMENT, 0, off ? 20 : 34);
  const sus = at(suspect, 12, 4);
  const hub = off ? HUB_OFF : HUB_ON;
  const groupTransform = off
    ? `translate(${SHIFT_OFF.x}px, ${SHIFT_OFF.y}px) scale(${SCALE_OFF})`
    : "translate(0px, 0px) scale(1)";
  const suspectOff = toGlobal(suspect, true);
  const suspectOn = toGlobal(suspect, false);

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
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="fde-ring"
        role="img"
        aria-label={`Case CR84920: ${RING_SIZE} accounts that all share one device and one payment method, and a public gateway that would merge ${HUB.collapsed} strangers into the ring unless it is collapsed.`}
      >
        <ellipse
          cx={432}
          cy={250}
          rx={374}
          ry={206}
          className="fde-ring-false-hull"
        />

        <g
          className="fde-ring-burst"
          style={{ transformOrigin: `${HUB_OFF.x}px ${HUB_OFF.y}px` }}
        >
          {others.map((p, i) => (
            <g key={i} style={{ transitionDelay: off ? `${i * 4}ms` : "0ms" }}>
              <path
                d={`M${HUB_OFF.x} ${HUB_OFF.y}L${p.x} ${p.y}`}
                className="fde-ring-burst-edge"
              />
              <circle
                cx={p.x}
                cy={p.y}
                r={2.5}
                className="fde-ring-burst-node"
              />
            </g>
          ))}
        </g>

        <g className="fde-ring-group" style={{ transform: groupTransform }}>
          <ellipse
            cx={400}
            cy={250}
            rx={330}
            ry={214}
            className="fde-ring-hull"
          />
          {accounts.map((p, i) => (
            <g key={i} className={i === SUSPECT ? "is-suspect" : undefined}>
              <path
                d={`M${DEVICE.x} ${DEVICE.y}C${DEVICE.x + 140} ${DEVICE.y} ${p.x - 120} ${p.y} ${p.x} ${p.y}`}
                className="fde-ring-edge fde-ring-edge-l"
              />
              <path
                d={`M${p.x} ${p.y}C${p.x + 120} ${p.y} ${PAYMENT.x - 140} ${PAYMENT.y} ${PAYMENT.x} ${PAYMENT.y}`}
                className="fde-ring-edge fde-ring-edge-r"
              />
            </g>
          ))}
          {accounts.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={i === SUSPECT ? 8 : 5}
              className={i === SUSPECT ? "fde-ring-suspect" : "fde-ring-node"}
            />
          ))}
          <rect
            x={DEVICE.x - 11}
            y={DEVICE.y - 11}
            width={22}
            height={22}
            className="fde-ring-key"
            transform={`rotate(45 ${DEVICE.x} ${DEVICE.y})`}
          />
          <rect
            x={PAYMENT.x - 10}
            y={PAYMENT.y - 10}
            width={20}
            height={20}
            className="fde-ring-key"
          />
        </g>

        <path
          className="fde-ring-flow fde-ring-flow-on"
          d={`M${suspectOn.x} ${suspectOn.y}Q${HUB_ON.x - 120} ${HUB_ON.y - 10} ${HUB_ON.x} ${HUB_ON.y}`}
        />
        <path
          className="fde-ring-flow fde-ring-flow-off"
          d={`M${suspectOff.x} ${suspectOff.y}Q${(suspectOff.x + HUB_OFF.x) / 2} ${suspectOff.y - 46} ${HUB_OFF.x} ${HUB_OFF.y}`}
        />

        <g
          className="fde-ring-hub"
          style={{ transform: `translate(${hub.x}px, ${hub.y}px)` }}
        >
          <circle r={off ? 13 : 9} className="fde-ring-hub-node" />
          <path d="M-5 -5L5 5M5 -5L-5 5" className="fde-ring-hub-x" />
        </g>

        <g className="fde-ring-labels">
          <text
            x={dev.x + (off ? -24 : 0)}
            y={dev.y}
            textAnchor={off ? "start" : "middle"}
            className="fde-ring-label fde-ring-label-dim fde-ring-id"
          >
            {SHARED_DEVICE}
          </text>
          <text
            x={pay.x + (off ? 24 : 0)}
            y={pay.y + (off ? 0 : 12)}
            textAnchor={off ? "end" : "middle"}
            className="fde-ring-label fde-ring-label-dim fde-ring-id"
          >
            {SHARED_PAYMENT}
          </text>
          <text x={sus.x} y={sus.y} className="fde-ring-label">
            {RING_SUSPECT}
          </text>
          <text
            x={off ? hub.x : hub.x + 14}
            y={off ? 52 : hub.y - 20}
            textAnchor={off ? "middle" : "end"}
            className="fde-ring-label"
          >
            {HUB.id} · degree {HUB.degree}
          </text>
          {off && (
            <text
              x={HUB_OFF.x}
              y={H - 18}
              textAnchor="middle"
              className="fde-ring-label fde-ring-label-warn"
            >
              +{HUB.collapsed} unrelated accounts
            </text>
          )}
        </g>

        <g className="fde-ring-axis" aria-hidden="true">
          <text x={DEVICE.x} y={H - 12} textAnchor="middle">
            Shared device
          </text>
          <text x={400} y={H - 12} textAnchor="middle">
            {RING_SIZE} accounts, each linked to both
          </text>
          <text x={PAYMENT.x} y={H - 12} textAnchor="middle">
            Shared payment method
          </text>
        </g>
      </svg>
      <figcaption className="fde-viz-cap">
        Engine output for case {RING_SUSPECT} in the seeded world. Ids are
        synthetic; degrees and counts are what the graph engine returned.
      </figcaption>
    </figure>
  );
}
