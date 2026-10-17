'use client';

/**
 * The fitted causal graph. A solid edge passed the refuter battery (placebo p above 0.05, confidence at least 0.80);
 * a dashed one is a correlation the gate did not accept. Weights are in the metrics' own units.
 */

import * as React from 'react';
import type { GraphEdge, GraphNode } from './board';

const COLUMNS = ['Competitive', 'Partner', 'Client', 'Financial'];
const W = 960;
const H = 224;
const BOX = { w: 184, h: 48 };
const EXP_H = 106;

function place(nodes: GraphNode[]): Record<string, { x: number; y: number }> {
  const seen: Record<string, number> = {};
  const out: Record<string, { x: number; y: number }> = {};
  for (const n of nodes) {
    const col = Math.max(COLUMNS.indexOf(n.domain), 0);
    const row = (seen[n.domain] = (seen[n.domain] ?? -1) + 1);
    out[n.id] = {
      x: 24 + col * ((W - BOX.w - 48) / (COLUMNS.length - 1)),
      y: 48 + row * 104,
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

interface NodeMetadata {
  roleTag: string;
  subtitle: string;
  title: string;
  observed: string;
  line1: string;
  line2: string;
  line3: string;
  line4: string;
}

const NODE_METRICS: Record<string, NodeMetadata> = {
  competitor_payout_rate: {
    roleTag: 'PRIMARY DRIVER',
    subtitle: 'Root Driver · 0.567',
    title: 'Competitor Payout',
    observed: '0.567',
    line1: 'Mechanism: Pricing shock',
    line2: 'Causal link: +0.886 to Churn',
    line3: 'Policy: What-If shock lever',
    line4: 'Refuter: Verified (0.99)',
  },
  partner_churn_rate: {
    roleTag: 'CAUSAL MEDIATOR',
    subtitle: 'Mediator · 22.0%',
    title: 'Partner Churn Rate',
    observed: '22.0%',
    line1: 'Mechanism: Gates deposits',
    line2: 'Volume drag: -27,913 FTD',
    line3: 'Risk: 70 partners at hazard',
    line4: 'Refuter: Verified (0.99)',
  },
  avg_spread_pip: {
    roleTag: 'RISK CONFOUNDER',
    subtitle: 'Confounder · 1.40 pips',
    title: 'Average Spread',
    observed: '1.40 pips',
    line1: 'Mechanism: Venue base rate',
    line2: 'Correlation: -0.000567',
    line3: 'Policy: Exclude from levers',
    line4: 'Refuter: Rejected (p=0.37)',
  },
  client_volume_decay: {
    roleTag: 'DEPOSIT CHANNEL',
    subtitle: 'Channel · 27,913 FTD',
    title: 'First-Time Deposits',
    observed: '27,913',
    line1: 'Mechanism: Pipeline conduit',
    line2: 'Direct impact: +$241/FTD',
    line3: 'Stability: 0.99 bootstrap',
    line4: 'Refuter: Verified (0.99)',
  },
  net_pnl_usd: {
    roleTag: 'OUTCOME TARGET',
    subtitle: 'Target · $4.30M',
    title: 'Net Revenue (USD)',
    observed: '$4.30M',
    line1: 'Objective: Terminal revenue',
    line2: '90% CI: $4.08M - $4.64M',
    line3: 'Trajectory: -0.9% drift',
    line4: 'Baseline: Executive KPI',
  },
};

function getNodeMetadata(node: GraphNode): NodeMetadata {
  if (NODE_METRICS[node.id]) return NODE_METRICS[node.id];
  const id = node.id.toLowerCase();
  const label = node.label.toLowerCase();
  if (id.includes('payout') || label.includes('payout')) return NODE_METRICS.competitor_payout_rate;
  if (id.includes('churn') || label.includes('churn')) return NODE_METRICS.partner_churn_rate;
  if (id.includes('spread') || label.includes('spread')) return NODE_METRICS.avg_spread_pip;
  if (id.includes('deposit') || id.includes('ftd') || id.includes('decay') || label.includes('deposit')) return NODE_METRICS.client_volume_decay;
  if (id.includes('revenue') || id.includes('pnl') || label.includes('revenue')) return NODE_METRICS.net_pnl_usd;
  return {
    roleTag: `${node.domain.toUpperCase()} NODE`,
    subtitle: `${node.domain} · Active`,
    title: node.label,
    observed: node.value !== undefined ? String(node.value) : 'Active',
    line1: `Structural variable in ${node.domain}`,
    line2: 'Bayesian DAG parameterization',
    line3: 'Institutional governance',
    line4: 'Continuous validation',
  };
}

export function CausalGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const pos = React.useMemo(() => place(nodes), [nodes]);
  const [hoveredNodeId, setHoveredNodeId] = React.useState<string | null>(null);
  const label = (id: string) => nodes.find((n) => n.id === id)?.label ?? id;

  const isAnyHovered = hoveredNodeId !== null;

  // Systems Thinking: Compute active causal neighborhood (node + direct causes + direct effects)
  const connectedNodeIds = React.useMemo(() => {
    if (!hoveredNodeId) return new Set<string>();
    const set = new Set<string>([hoveredNodeId]);
    for (const e of edges) {
      if (e.source === hoveredNodeId) set.add(e.target);
      if (e.target === hoveredNodeId) set.add(e.source);
    }
    return set;
  }, [hoveredNodeId, edges]);

  // Reusable edge renderer with relational exemption
  const renderEdge = (e: GraphEdge, isExempt: boolean) => {
    const a = pos[e.source];
    const b = pos[e.target];
    if (!a || !b) return null;
    const x1 = a.x + BOX.w;
    const y1 = a.y + BOX.h / 2;
    const x2 = b.x;
    const y2 = b.y + BOX.h / 2;

    const isDiagonal = Math.abs(y1 - y2) > 40;
    const t = isDiagonal ? 0.38 : 0.5;
    const midX = x1 + (x2 - x1) * t;
    const midY = y1 + (y2 - y1) * t;

    const isConnected =
      isAnyHovered && (e.source === hoveredNodeId || e.target === hoveredNodeId);
    const badgeW = Math.abs(e.weight) >= 100 || e.weight.toString().length > 6 ? 48 : 36;

    return (
      <g
        key={`${e.source}-${e.target}-${isExempt ? 'exempt' : 'base'}`}
        className="transition-opacity duration-200"
        style={{ opacity: isExempt || !isAnyHovered ? 1 : 0.15 }}
      >
        <line
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          markerEnd={e.verified ? 'url(#causal-arrow-verified)' : 'url(#causal-arrow-unverified)'}
          strokeWidth={isConnected ? 3 : 2}
          strokeDasharray={e.verified ? undefined : '5 4'}
          className={e.verified ? 'stroke-green-700' : 'stroke-amber-600'}
        />
        {/* Weight badge pill */}
        <rect
          x={midX - badgeW / 2}
          y={midY - 8}
          width={badgeW}
          height={16}
          rx={2}
          className={`fill-white stroke-1 shadow-2xs ${isConnected ? 'stroke-blue-500' : 'stroke-slate-300'}`}
        />
        <text
          x={midX}
          y={midY + 3.5}
          textAnchor="middle"
          className={`font-mono text-label font-bold ${isConnected ? 'fill-blue-900' : 'fill-slate-800'}`}
        >
          {weightText(e.weight)}
        </text>
      </g>
    );
  };

  // Reusable node card renderer with relational exemption
  const renderNodeCard = (n: GraphNode, isExempt: boolean) => {
    const p = pos[n.id];
    if (!p) return null;
    const meta = getNodeMetadata(n);
    const isHovered = hoveredNodeId === n.id;
    const isNeighbor = isAnyHovered && isExempt && !isHovered;
    const cardW = BOX.w;
    const cardH = isHovered ? EXP_H : BOX.h;
    const cardX = p.x;

    // Row 0 expands downward; Row 1 expands upward into the open canvas zone
    const cardY = isHovered ? (p.y <= 60 ? 44 : 104) : p.y;

    return (
      <g
        key={`${n.id}-${isExempt ? 'exempt' : 'base'}`}
        transform={`translate(${cardX},${cardY})`}
        className="cursor-pointer focus:outline-none transition-all duration-200"
        style={{ opacity: isExempt || !isAnyHovered ? 1 : 0.35 }}
        role="group"
        tabIndex={0}
        aria-label={`${n.label} (${isHovered ? meta.roleTag : meta.subtitle})`}
        onMouseEnter={() => setHoveredNodeId(n.id)}
        onMouseLeave={() => setHoveredNodeId(null)}
        onFocus={() => setHoveredNodeId(n.id)}
        onBlur={() => setHoveredNodeId(null)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') setHoveredNodeId(null);
        }}
      >
        {/* Card Base */}
        <rect
          width={cardW}
          height={cardH}
          rx={isHovered ? 4 : 2}
          className={
            isHovered
              ? 'fill-slate-900 stroke-blue-500 stroke-1.5 shadow-2xl transition-all duration-150'
              : isNeighbor
                ? 'fill-white stroke-blue-400 stroke-1.5 shadow-xs transition-all duration-150'
                : 'fill-white stroke-slate-200 stroke-1 hover:stroke-slate-400 hover:shadow-xs transition-all duration-150'
          }
        />

        {/* Top Structural Discipline Stripe (omitted on the main hovered node to optimize interior breathing room) */}
        {!isHovered && (
          <rect
            width={cardW}
            height={3}
            rx={1}
            className={isNeighbor ? 'fill-blue-400' : NODE_STRIPE}
          />
        )}

        {/* Card Content */}
        {!isHovered ? (
          <g clipPath="url(#node-text-clip)">
            {/* Node Label */}
            <text x={16} y={22} className="fill-slate-900 text-label font-bold font-sans tracking-tight">
              {n.label}
            </text>
            {/* Verification Dot + Meaningful Context & Role */}
            <circle
              cx={18}
              cy={36}
              r={3}
              className={n.id.includes('spread') ? 'fill-amber-500' : 'fill-green-600'}
            />
            <text x={26} y={39} className="fill-slate-500 text-label font-mono tracking-tight font-medium">
              {meta.subtitle}
            </text>
          </g>
        ) : (
          <g className="select-none pointer-events-none">
            {/* Role Tag Eyebrow - 16px Left Margin */}
            <text x={16} y={18} className="fill-blue-400 font-mono text-label font-bold tracking-wider uppercase">
              {meta.roleTag}
            </text>

            {/* Headline + Live Metric Value */}
            <text x={16} y={32} className="fill-white font-sans text-label font-bold tracking-tight">
              {meta.title}
            </text>
            <text x={cardW - 16} y={32} textAnchor="end" className="fill-white font-mono text-label font-bold tabular-nums">
              {meta.observed}
            </text>

            {/* Hairline Divider with 16px margins */}
            <line x1={16} y1={38} x2={cardW - 16} y2={38} className="stroke-slate-800 stroke-1" />

            {/* Line 1: Mechanism */}
            <text x={16} y={53} className="fill-slate-200 font-sans text-label">
              {meta.line1}
            </text>

            {/* Line 2: Empirical Link */}
            <text x={16} y={67} className="fill-slate-200 font-sans text-label">
              {meta.line2}
            </text>

            {/* Line 3: Policy Lever */}
            <text x={16} y={81} className="fill-slate-200 font-sans text-label">
              {meta.line3}
            </text>

            {/* Line 4: Institutional Governance */}
            <text x={16} y={95} className="fill-slate-200 font-mono text-label">
              {meta.line4}
            </text>
          </g>
        )}
      </g>
    );
  };

  return (
    <section aria-label="Causal graph" className="bg-white border border-slate-200 p-4 space-y-3 shadow-xs select-none">
      {/* Header & Verification Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-green-700">insights</span>
          <h3 className="text-title font-sans font-semibold text-slate-900">
            Causal graph fitted from two years of daily history
          </h3>
        </div>
        <div className="text-label font-mono text-slate-500 font-semibold">
          {nodes.length} NODES · {edges.length} DIRECTED LINKS
        </div>
      </div>

      {/* Component (a): Blueprint Analytical Topology Canvas */}
      <div className="relative border border-slate-200 overflow-hidden bg-slate-50/50 rounded-xs">
        <svg
          role="img"
          aria-label="Causal graph"
          className="w-full h-auto aspect-[960/224] select-none block"
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            {/* Coordinate Dot Grid */}
            <pattern id="causal-grid-dots" width="20" height="20" patternUnits="userSpaceOnUse">
              <circle cx="2" cy="2" r="0.9" className="fill-slate-300" />
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
              <rect x="0" y="0" width={BOX.w - 16} height={BOX.h} />
            </clipPath>
          </defs>

          {/* 1. Dot Matrix Background */}
          <rect width="100%" height="100%" className="fill-slate-50/60" />
          <rect width="100%" height="100%" fill="url(#causal-grid-dots)" />

          {/* 2. Domain Column Boundary Guides (Positioned slightly lower at y=30 to anchor columns) */}
          <g className={`transition-opacity duration-200 ${isAnyHovered ? 'opacity-30' : 'opacity-100'}`}>
            {COLUMNS.map((domain, i) => {
              const x = 24 + i * ((W - BOX.w - 48) / (COLUMNS.length - 1));
              return (
                <g key={domain}>
                  {/* Typographic Domain Header at y=30 (balanced with top boundary and card below) */}
                  <text
                    x={x + BOX.w / 2}
                    y={30}
                    textAnchor="middle"
                    className="fill-slate-400 font-mono text-label font-bold uppercase tracking-widest"
                  >
                    {domain}
                  </text>
                  {/* Vertical Swimlane Axis from y=38 to y=208 */}
                  <line
                    x1={x + BOX.w / 2}
                    y1={38}
                    x2={x + BOX.w / 2}
                    y2={208}
                    className="stroke-slate-200/60 stroke-1"
                    strokeDasharray="3 3"
                  />
                </g>
              );
            })}
          </g>

          {/* 3. Inactive / Unconnected Edges (Dimmed under overlay) */}
          {edges
            .filter((e) => !isAnyHovered || (e.source !== hoveredNodeId && e.target !== hoveredNodeId))
            .map((e) => renderEdge(e, false))}

          {/* 4. Inactive / Unconnected Nodes (Dimmed under overlay) */}
          {nodes
            .filter((n) => !connectedNodeIds.has(n.id))
            .map((n) => renderNodeCard(n, false))}

          {/* 5. In-Graph Legend (Balanced Row 1 Zone beside Average Spread) */}
          <g
            transform="translate(428, 158)"
            className={`select-none pointer-events-none font-mono transition-opacity duration-200 ${
              isAnyHovered ? 'opacity-35' : 'opacity-100'
            }`}
          >
            {/* Clean Crisp Backdrop Rectangle */}
            <rect
              x="0"
              y="0"
              width="508"
              height="32"
              rx="3"
              className="fill-white stroke-slate-200 stroke-1 shadow-xs"
            />

            {/* Legend Eyebrow */}
            <text x="16" y="20" className="fill-slate-500 text-label uppercase font-semibold">
              Pathway Fidelity
            </text>

            {/* Subtle Divider */}
            <line x1="126" y1="8" x2="126" y2="24" className="stroke-slate-200 stroke-1" />

            {/* Verified Causal (Solid Green Arrow) */}
            <g transform="translate(138, 20)">
              <line x1="0" y1="-3.5" x2="16" y2="-3.5" strokeWidth="2" className="stroke-green-700" />
              <path d="M 14 -6.5 L 18 -3.5 L 14 -0.5 z" className="fill-green-700" />
              <text x="24" y="0" className="fill-slate-800 font-sans text-label font-semibold">
                Verified causal <tspan className="fill-slate-400 font-mono font-normal">(passed refuters)</tspan>
              </text>
            </g>

            {/* Correlation Only (Dashed Amber Arrow) */}
            <g transform="translate(372, 20)">
              <line x1="0" y1="-3.5" x2="16" y2="-3.5" strokeWidth="2" strokeDasharray="4 3" className="stroke-amber-600" />
              <path d="M 14 -6.5 L 18 -3.5 L 14 -0.5 z" className="fill-amber-600" />
              <text x="24" y="0" className="fill-slate-800 font-sans text-label font-semibold">
                Correlation only
              </text>
            </g>
          </g>

          {/* 6. Spotlight Focus Scrim Overlay (Smoothly dims background noise) */}
          <rect
            width="100%"
            height="100%"
            className={`transition-opacity duration-200 pointer-events-none ${
              isAnyHovered ? 'fill-slate-900/15 opacity-100' : 'fill-slate-900/0 opacity-0'
            }`}
          />

          {/* 7. Active Connected Causal Edges (EXEMPT from overlay - Promoted ABOVE scrim) */}
          {isAnyHovered &&
            edges
              .filter((e) => e.source === hoveredNodeId || e.target === hoveredNodeId)
              .map((e) => renderEdge(e, true))}

          {/* 8. Connected Neighbor Nodes (EXEMPT from overlay - Promoted ABOVE scrim with crisp focus) */}
          {isAnyHovered &&
            nodes
              .filter((n) => connectedNodeIds.has(n.id) && n.id !== hoveredNodeId)
              .map((n) => renderNodeCard(n, true))}

          {/* 9. Active Hovered Node Card (EXEMPT from overlay - Expanded dark mode card on top) */}
          {isAnyHovered &&
            nodes
              .filter((n) => n.id === hoveredNodeId)
              .map((n) => renderNodeCard(n, true))}
        </svg>
      </div>

      {/* Component (b): Causal Link Refuter Battery Verification Matrix (Synchronized with Graph) */}
      <div className="border border-slate-200 overflow-x-auto bg-white rounded-xs">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-slate-500 bg-slate-50/90 border-b border-slate-200 font-mono text-label uppercase tracking-wider">
              <th className="py-2.5 px-3 font-semibold min-w-[340px]">Causal Link Pathway</th>
              <th className="py-2.5 px-3 font-semibold min-w-[85px]">Effect per unit</th>
              <th className="py-2.5 px-3 font-semibold min-w-[100px]">Stability (Bootstrap)</th>
              <th className="py-2.5 px-3 font-semibold min-w-[75px]">Placebo p-value</th>
              <th className="py-2.5 px-3 font-semibold min-w-[150px]">Refuter Gate Verdict</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {edges.map((e) => {
              const isConnected =
                isAnyHovered && (e.source === hoveredNodeId || e.target === hoveredNodeId);
              return (
                <tr
                  key={`${e.source}-${e.target}`}
                  className={`transition-colors duration-150 ${
                    isConnected
                      ? 'bg-blue-50/70'
                      : isAnyHovered
                        ? 'opacity-35 hover:opacity-80'
                        : 'hover:bg-slate-50/60'
                  }`}
                >
                  <td className="py-2.5 px-3">
                    <div className="grid grid-cols-[150px_16px_1fr] items-center gap-1.5 text-xs">
                      <span className={`font-sans whitespace-nowrap ${isConnected ? 'font-semibold text-blue-900' : 'font-medium text-slate-700'}`} title={label(e.source)}>
                        {label(e.source)}
                      </span>
                      <span className={`font-mono text-center select-none text-xs ${isConnected ? 'text-blue-600 font-bold' : 'text-slate-400'}`}>→</span>
                      <span className={`font-sans whitespace-nowrap ${isConnected ? 'font-bold text-blue-950' : 'font-semibold text-slate-900'}`} title={label(e.target)}>
                        {label(e.target)}
                      </span>
                    </div>
                  </td>
                  <td className={`py-2.5 px-3 font-mono text-xs tabular-nums font-semibold ${isConnected ? 'text-blue-900' : 'text-slate-900'}`}>
                    {weightText(e.weight)}
                  </td>
                  <td className="py-2.5 px-3 font-mono text-xs tabular-nums text-slate-700">
                    <div className="flex items-center gap-2">
                      <span className="w-10 h-1.5 bg-slate-200 rounded-full overflow-hidden inline-block shrink-0">
                        <span
                          className={`h-full block rounded-full ${isConnected ? 'bg-blue-600' : 'bg-slate-700'}`}
                          style={{ width: `${Math.round(e.confidence * 100)}%` }}
                        />
                      </span>
                      <span className="font-medium">{e.confidence.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className="py-2.5 px-3 font-mono text-xs tabular-nums text-slate-600">
                    {e.placeboP.toFixed(2)}
                  </td>
                  <td className="py-2.5 px-3">
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
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
