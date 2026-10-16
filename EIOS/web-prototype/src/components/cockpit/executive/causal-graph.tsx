'use client';

/**
 * The fitted causal graph. A solid edge passed the refuter battery (placebo p above 0.05, confidence at least 0.80);
 * a dashed one is a correlation the gate did not accept. Weights are in the metrics' own units.
 */

import * as React from 'react';
import type { GraphEdge, GraphNode } from './board';

const COLUMNS = ['Competitive', 'Partner', 'Client', 'Financial'];
const W = 960;
const H = 200;
const BOX = { w: 168, h: 48 };

function place(nodes: GraphNode[]): Record<string, { x: number; y: number }> {
  const seen: Record<string, number> = {};
  const out: Record<string, { x: number; y: number }> = {};
  for (const n of nodes) {
    const col = Math.max(COLUMNS.indexOf(n.domain), 0);
    const row = (seen[n.domain] = (seen[n.domain] ?? -1) + 1);
    out[n.id] = {
      x: 20 + col * ((W - BOX.w - 40) / (COLUMNS.length - 1)),
      y: 30 + row * 84,
    };
  }
  return out;
}

function weightText(w: number): string {
  const a = Math.abs(w);
  return `${w > 0 ? '+' : '-'}${a >= 100 ? Math.round(a).toLocaleString('en-US') : a.toPrecision(3)}`;
}

// Unified institutional node stripe (Palantir & QuantumBlack standard)
const NODE_STRIPE = 'fill-slate-800';

export function CausalGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const pos = React.useMemo(() => place(nodes), [nodes]);
  const label = (id: string) => nodes.find((n) => n.id === id)?.label ?? id;

  return (
    <section aria-label="Causal graph" className="bg-white border border-slate-200 p-4 space-y-3.5 shadow-xs select-none">
      {/* Header & Verification Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-green-700">insights</span>
          <h3 className="text-title font-sans font-semibold text-slate-900">
            Causal graph fitted from two years of daily history
          </h3>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-label font-mono">
          <span className="flex items-center gap-1.5 text-green-800 font-semibold bg-green-50 px-2 py-0.5 border border-green-200">
            <span className="w-3.5 h-0.5 bg-green-700 inline-block" />
            Verified causal
          </span>
          <span className="flex items-center gap-1.5 text-amber-800 font-semibold bg-amber-50 px-2 py-0.5 border border-amber-200">
            <span className="w-3.5 border-t border-dashed border-amber-600 inline-block" />
            Correlation only
          </span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-500 font-semibold">
            {nodes.length} NODES · {edges.length} DIRECTED LINKS
          </span>
        </div>
      </div>

      {/* Blueprint Analytical Topology Canvas */}
      <div className="relative border border-slate-200 overflow-hidden bg-slate-50">
        <svg
          role="img"
          aria-label="Causal graph"
          className="w-full h-56 select-none"
          viewBox={`0 0 ${W} ${H}`}
        >
          <defs>
            {/* Coordinate Dot Grid */}
            <pattern id="causal-grid-dots" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="1" className="fill-slate-300" />
            </pattern>
            {/* Arrowheads */}
            <marker id="causal-arrow-verified" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M 0 2 L 6 5 L 0 8 z" className="fill-green-700" />
            </marker>
            <marker id="causal-arrow-unverified" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M 0 2 L 6 5 L 0 8 z" className="fill-amber-600" />
            </marker>
            {/* Accessible Node Content Clipping Protection */}
            <clipPath id="node-text-clip">
              <rect x="0" y="0" width={BOX.w - 12} height={BOX.h} />
            </clipPath>
          </defs>

          {/* Dot Matrix Background */}
          <rect width="100%" height="100%" className="fill-slate-50" />
          <rect width="100%" height="100%" fill="url(#causal-grid-dots)" />

          {/* Domain Column Boundary Guides */}
          {COLUMNS.map((domain, i) => {
            const x = 20 + i * ((W - BOX.w - 40) / (COLUMNS.length - 1));
            return (
              <g key={domain}>
                <line x1={x + BOX.w / 2} y1={0} x2={x + BOX.w / 2} y2={H} className="stroke-slate-200 stroke-1" strokeDasharray="3 3" />
                <text x={x + BOX.w / 2} y={16} textAnchor="middle" className="fill-slate-400 font-mono text-label font-bold uppercase tracking-wider">
                  {domain}
                </text>
              </g>
            );
          })}

          {/* Directed Causal Edges */}
          {edges.map((e) => {
            const a = pos[e.source];
            const b = pos[e.target];
            if (!a || !b) return null;
            const x1 = a.x + BOX.w;
            const y1 = a.y + BOX.h / 2;
            const x2 = b.x;
            const y2 = b.y + BOX.h / 2;
            const midX = (x1 + x2) / 2;
            const midY = (y1 + y2) / 2;

            return (
              <g key={`${e.source}-${e.target}`}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  markerEnd={e.verified ? 'url(#causal-arrow-verified)' : 'url(#causal-arrow-unverified)'}
                  strokeWidth={2}
                  strokeDasharray={e.verified ? undefined : '5 4'}
                  className={e.verified ? 'stroke-green-700' : 'stroke-amber-600'}
                />
                {/* Weight badge pill */}
                <rect
                  x={midX - 20}
                  y={midY - 8}
                  width={40}
                  height={16}
                  rx={2}
                  className="fill-white stroke-slate-300 stroke-1"
                />
                <text
                  x={midX}
                  y={midY + 3.5}
                  textAnchor="middle"
                  className="fill-slate-800 font-mono text-label font-bold"
                >
                  {weightText(e.weight)}
                </text>
              </g>
            );
          })}

          {/* Institutional Node Cards */}
          {nodes.map((n) => {
            const p = pos[n.id];
            if (!p) return null;
            return (
              <g
                key={n.id}
                transform={`translate(${p.x},${p.y})`}
                className="cursor-pointer"
                role="group"
                aria-label={`${n.label} (${n.domain})`}
              >
                <title>{n.label} — {n.domain}</title>
                {/* Card Base */}
                <rect
                  width={BOX.w}
                  height={BOX.h}
                  rx={2}
                  className="fill-white stroke-slate-300 stroke-1 hover:stroke-slate-500 transition-colors"
                />
                {/* Unified Structural Accent Stripe (Palantir & QuantumBlack standard) */}
                <rect width={BOX.w} height={3} rx={1} className={NODE_STRIPE} />
                {/* Accessible Text Container with Guaranteed Bounds */}
                <g clipPath="url(#node-text-clip)">
                  {/* Node Label */}
                  <text x={10} y={23} className="fill-slate-900 text-label font-bold font-sans tracking-tight">
                    {n.label}
                  </text>
                  {/* Node Domain */}
                  <text x={10} y={38} className="fill-slate-500 text-label font-mono tracking-wider uppercase font-semibold">
                    {n.domain}
                  </text>
                </g>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Causal Link Refuter Battery Verification Matrix */}
      <div className="border border-slate-200 overflow-x-auto bg-white">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-slate-500 bg-slate-50/90 border-b border-slate-200 font-mono text-label uppercase tracking-wider">
              <th className="py-2.5 px-2.5 font-semibold min-w-[340px]">Causal Link Pathway</th>
              <th className="py-2.5 px-2.5 font-semibold min-w-[85px]">Effect per unit</th>
              <th className="py-2.5 px-2.5 font-semibold min-w-[100px]">Stability (Bootstrap)</th>
              <th className="py-2.5 px-2.5 font-semibold min-w-[75px]">Placebo p-value</th>
              <th className="py-2.5 px-2.5 font-semibold min-w-[150px]">Refuter Gate Verdict</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {edges.map((e) => (
              <tr key={`${e.source}-${e.target}`} className="hover:bg-slate-50/60 transition-colors">
                <td className="py-2.5 px-2.5">
                  <div className="grid grid-cols-[150px_16px_1fr] items-center gap-1.5 text-xs">
                    <span className="font-sans font-medium text-slate-700 whitespace-nowrap" title={label(e.source)}>
                      {label(e.source)}
                    </span>
                    <span className="text-slate-400 font-mono text-center select-none text-xs">→</span>
                    <span className="font-sans font-semibold text-slate-900 whitespace-nowrap" title={label(e.target)}>
                      {label(e.target)}
                    </span>
                  </div>
                </td>
                <td className="py-2.5 px-2.5 font-mono text-xs tabular-nums font-semibold text-slate-900">
                  {weightText(e.weight)}
                </td>
                <td className="py-2.5 px-2.5 font-mono text-xs tabular-nums text-slate-700">
                  <div className="flex items-center gap-2">
                    <span className="w-10 h-1.5 bg-slate-200 rounded-full overflow-hidden inline-block shrink-0">
                      <span
                        className="h-full bg-blue-600 block rounded-full"
                        style={{ width: `${Math.round(e.confidence * 100)}%` }}
                      />
                    </span>
                    <span className="font-medium">{e.confidence.toFixed(2)}</span>
                  </div>
                </td>
                <td className="py-2.5 px-2.5 font-mono text-xs tabular-nums text-slate-600">
                  {e.placeboP.toFixed(2)}
                </td>
                <td className="py-2.5 px-2.5">
                  <div className="flex items-center gap-2 text-xs font-semibold whitespace-nowrap">
                    <span
                      className={`w-2 h-2 rounded-full shrink-0 ${
                        e.verified ? 'bg-green-600' : 'bg-amber-600'
                      }`}
                    />
                    <span className={e.verified ? 'text-green-700 font-sans' : 'text-amber-800 font-sans'}>
                      {e.verified ? (
                        e.label
                      ) : (
                        <>
                          <span className="sr-only">{e.label}</span>
                          <span aria-hidden="true">{e.label.includes('Correlation') ? 'Correlation' : e.label}</span>
                        </>
                      )}
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
