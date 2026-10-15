'use client';

/**
 * The fitted causal graph. A solid edge passed the refuter battery (placebo p above 0.05, confidence at least 0.80);
 * a dashed one is a correlation the gate did not accept. Weights are in the metrics' own units.
 */

import * as React from 'react';
import type { GraphEdge, GraphNode } from './board';

const COLUMNS = ['Competitive', 'Partner', 'Client', 'Financial'];
const W = 700;
const H = 210;
const BOX = { w: 150, h: 46 };

function place(nodes: GraphNode[]): Record<string, { x: number; y: number }> {
  const seen: Record<string, number> = {};
  const out: Record<string, { x: number; y: number }> = {};
  for (const n of nodes) {
    const col = Math.max(COLUMNS.indexOf(n.domain), 0);
    const row = (seen[n.domain] = (seen[n.domain] ?? -1) + 1);
    out[n.id] = { x: 20 + col * ((W - BOX.w - 40) / (COLUMNS.length - 1)), y: 20 + row * 96 };
  }
  return out;
}

function weightText(w: number): string {
  const a = Math.abs(w);
  return `${w > 0 ? '+' : '-'}${a >= 100 ? Math.round(a).toLocaleString('en-US') : a.toPrecision(3)}`;
}

export function CausalGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const pos = React.useMemo(() => place(nodes), [nodes]);
  const label = (id: string) => nodes.find((n) => n.id === id)?.label ?? id;
  return (
    <section aria-label="Causal graph" className="bg-white border border-cx-line p-4 space-y-3 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cx-line-soft pb-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-cx-ok">insights</span>
          <h3 className="text-title font-sans font-semibold text-cx-ink">Causal graph fitted from two years of daily history</h3>
        </div>
        <div className="flex items-center gap-3 text-label font-mono">
          <span className="flex items-center gap-1.5 text-cx-ok">
            <span className="w-5 h-0.5 bg-cx-ok-solid inline-block" />
            Verified causal
          </span>
          <span className="flex items-center gap-1.5 text-cx-warn">
            <span className="w-5 border-t border-dashed border-cx-warn-solid inline-block" />
            Correlation only
          </span>
        </div>
      </div>
      <svg role="img" aria-label="Causal graph" className="w-full h-52 bg-cx-sub border border-cx-line" viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <marker id="exec-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M 0 2 L 8 5 L 0 8 z" className="fill-slate-500" />
          </marker>
        </defs>
        {edges.map((e) => {
          const a = pos[e.source];
          const b = pos[e.target];
          if (!a || !b) return null;
          return (
            <line
              key={`${e.source}-${e.target}`}
              x1={a.x + BOX.w}
              y1={a.y + BOX.h / 2}
              x2={b.x}
              y2={b.y + BOX.h / 2}
              markerEnd="url(#exec-arrow)"
              strokeWidth={1.5}
              strokeDasharray={e.verified ? undefined : '5 4'}
              className={e.verified ? 'stroke-green-700' : 'stroke-amber-600'}
            />
          );
        })}
        {nodes.map((n) => (
          <g key={n.id} transform={`translate(${pos[n.id].x},${pos[n.id].y})`}>
            <rect width={BOX.w} height={BOX.h} className="fill-white stroke-slate-300" />
            <text x={6} y={19} className="fill-slate-900 text-label font-semibold">
              {n.label}
            </text>
            <text x={6} y={36} className="fill-slate-500 text-label font-mono">
              {n.domain}
            </text>
          </g>
        ))}
      </svg>
      <table className="w-full text-label font-mono">
        <thead>
          <tr className="text-left text-cx-muted border-b border-cx-line-soft">
            <th className="py-1 font-semibold">Link</th>
            <th className="font-semibold">Effect per unit</th>
            <th className="font-semibold">Stability</th>
            <th className="font-semibold">Placebo p</th>
            <th className="font-semibold">Verdict</th>
          </tr>
        </thead>
        <tbody>
          {edges.map((e) => (
            <tr key={`${e.source}-${e.target}`} className="border-b border-cx-line-soft align-top">
              <td className="py-1 pr-2 text-cx-ink">
                {label(e.source)} → {label(e.target)}
              </td>
              <td className="tabular-nums">{weightText(e.weight)}</td>
              <td className="tabular-nums">{e.confidence.toFixed(2)}</td>
              <td className="tabular-nums">{e.placeboP.toFixed(2)}</td>
              <td className={e.verified ? 'text-cx-ok font-semibold' : 'text-cx-warn font-semibold'}>{e.label}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
