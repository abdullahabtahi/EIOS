'use client';

/**
 * Causal DAG Canvas
 * Enforces Constitution Principle III (Causal Refutation Before Action).
 * Distinguishes verified causal edges (solid emerald, DoWhy refuter placebo p > 0.05)
 * from mere statistical correlations (dashed amber, p <= 0.05).
 * Strict Institutional Light-Mode styling.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { CausalNode, CausalEdge } from '../state/cockpit-types';

const DEFAULT_NODES: CausalNode[] = [
  { id: 'broker_fee_bps', domain: 'COMPETITIVE', label: 'Broker Fee Spread', baseValue: 12.0, shockedValue: 18.0, unit: 'bps', isDirectTarget: true },
  { id: 'latam_flow_vol', domain: 'PARTNER', label: 'LatAm Partner Flow', baseValue: 450.0, shockedValue: 395.0, unit: '$M', isDirectTarget: false },
  { id: 'client_churn_p', domain: 'CLIENT', label: 'Client Churn Hazard', baseValue: 0.04, shockedValue: 0.082, unit: '%', isDirectTarget: false },
  { id: 'net_brokerage_pnl', domain: 'FINANCIAL', label: 'Net Brokerage P&L', baseValue: 84.5, shockedValue: 71.2, unit: '$M', isDirectTarget: false },
];

const DEFAULT_EDGES: CausalEdge[] = [
  {
    id: 'e1',
    source: 'broker_fee_bps',
    target: 'latam_flow_vol',
    coefficient: -9.16,
    pValue: 0.001,
    placeboRefuterPValue: 0.42, // > 0.05 => VERIFIED CAUSAL
    confidence: 0.94,
    status: 'VERIFIED_CAUSAL',
  },
  {
    id: 'e2',
    source: 'latam_flow_vol',
    target: 'net_brokerage_pnl',
    coefficient: 0.18,
    pValue: 0.002,
    placeboRefuterPValue: 0.38, // > 0.05 => VERIFIED CAUSAL
    confidence: 0.89,
    status: 'VERIFIED_CAUSAL',
  },
  {
    id: 'e3',
    source: 'broker_fee_bps',
    target: 'client_churn_p',
    coefficient: 0.007,
    pValue: 0.04,
    placeboRefuterPValue: 0.03, // <= 0.05 => CORRELATION ONLY
    confidence: 0.65,
    status: 'CORRELATION_ONLY',
  },
];

export function CausalDagCanvas() {
  const { state } = useCockpit();
  const [selectedEdge, setSelectedEdge] = React.useState<CausalEdge | null>(null);

  // Dynamic values adjusted by what-if feeShockBps
  const shockBps = state.whatIfParams.feeShockBps;

  const nodes = React.useMemo(() => {
    return DEFAULT_NODES.map((n) => {
      if (n.id === 'broker_fee_bps') {
        return { ...n, shockedValue: n.baseValue + shockBps };
      }
      if (n.id === 'latam_flow_vol') {
        return { ...n, shockedValue: +(n.baseValue - shockBps * 4.5).toFixed(1) };
      }
      if (n.id === 'net_brokerage_pnl') {
        return { ...n, shockedValue: +(n.baseValue - shockBps * 1.1).toFixed(1) };
      }
      return n;
    });
  }, [shockBps]);

  return (
    <div className="bg-white border border-slate-200 p-4 shadow-sm space-y-3">
      {/* Header & Principle III Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-sharp text-base text-emerald-700">insights</span>
            <h3 className="text-xs font-bold font-mono uppercase tracking-wide text-slate-900">
              Interactive 4-Domain Causal Directed Acyclic Graph (DAG)
            </h3>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5 font-sans">
            Constitution Principle III: Refuter-passed causal vectors vs observational correlations.
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-[10px] font-mono">
          <span className="flex items-center gap-1.5 text-[#0D8050]">
            <span className="w-5 h-0.5 bg-[#0F9960] inline-block" />
            Solid: Verified Causal (p &gt; 0.05)
          </span>
          <span className="flex items-center gap-1.5 text-[#A66321]">
            <span className="w-5 h-0.5 border-t border-dashed border-[#D9822B] inline-block" />
            Dashed: Correlation Only
          </span>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full h-64 bg-slate-50 border border-[#D8E1E8] overflow-hidden">
        <svg className="w-full h-full" viewBox="0 0 700 240">
          <defs>
            <marker
              id="arrow-causal"
              viewBox="0 0 10 10"
              refX="7"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M 0 2 L 8 5 L 0 8 z" fill="#0F9960" />
            </marker>
            <marker
              id="arrow-correlation"
              viewBox="0 0 10 10"
              refX="7"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto"
            >
              <path d="M 0 2 L 8 5 L 0 8 z" fill="#d97706" />
            </marker>
          </defs>

          {/* Edges */}
          {/* Edge 1: Broker Fee (190, 80) -> LatAm Flow (320, 80) */}
          <g
            className="cursor-pointer group"
            onClick={() => setSelectedEdge(DEFAULT_EDGES[0])}
          >
            <line
              x1="190"
              y1="80"
              x2="315"
              y2="80"
              stroke="#059669"
              strokeWidth="2.5"
              markerEnd="url(#arrow-causal)"
              className="group-hover:stroke-emerald-800 transition-colors"
            />
            <rect x="210" y="66" width="90" height="16" fill="#f0fdf4" stroke="#86efac" strokeWidth="1" />
            <text x="255" y="78" fill="#065f46" fontSize="9" fontWeight="bold" fontFamily="monospace" textAnchor="middle" dominantBaseline="middle">
              β=-9.16 (p=0.42)
            </text>
          </g>

          {/* Edge 2: LatAm Flow (450, 80) -> Net PnL (540, 80) */}
          <g
            className="cursor-pointer group"
            onClick={() => setSelectedEdge(DEFAULT_EDGES[1])}
          >
            <line
              x1="450"
              y1="80"
              x2="535"
              y2="80"
              stroke="#059669"
              strokeWidth="2.5"
              markerEnd="url(#arrow-causal)"
              className="group-hover:stroke-emerald-800 transition-colors"
            />
            <rect x="458" y="66" width="70" height="16" fill="#f0fdf4" stroke="#86efac" strokeWidth="1" />
            <text x="493" y="78" fill="#065f46" fontSize="9" fontWeight="bold" fontFamily="monospace" textAnchor="middle" dominantBaseline="middle">
              β=+0.18 (p=0.38)
            </text>
          </g>

          {/* Edge 3: Broker Fee (190, 100) -> Client Churn (320, 180) */}
          <g
            className="cursor-pointer group"
            onClick={() => setSelectedEdge(DEFAULT_EDGES[2])}
          >
            <path
              d="M 190 98 C 240 115, 260 155, 315 178"
              stroke="#d97706"
              strokeWidth="2"
              strokeDasharray="4 3"
              fill="none"
              markerEnd="url(#arrow-correlation)"
              className="group-hover:stroke-amber-700 transition-colors"
            />
            <rect x="180" y="146" width="130" height="16" fill="#fffbeb" stroke="#fcd34d" strokeWidth="1" />
            <text x="245" y="158" fill="#92400e" fontSize="9" fontWeight="bold" fontFamily="monospace" textAnchor="middle" dominantBaseline="middle">
              Correlation (refuter fail)
            </text>
          </g>

          {/* Nodes */}
          {/* Node 1: Broker Fee */}
          <g transform="translate(60, 45)">
            <rect width="130" height="70" fill="#ffffff" stroke="#0284c7" strokeWidth="2" />
            <rect width="130" height="18" fill="#e0f2fe" />
            <text x="8" y="13" fill="#0369a1" fontSize="9" fontWeight="bold" fontFamily="monospace">
              COMPETITIVE
            </text>
            <text x="8" y="36" fill="#0f172a" fontSize="10" fontWeight="bold">
              {nodes[0].label}
            </text>
            <text x="8" y="56" fill="#0284c7" fontSize="13" fontWeight="bold" fontFamily="monospace">
              {nodes[0].shockedValue} {nodes[0].unit}
            </text>
          </g>

          {/* Node 2: LatAm Flow */}
          <g transform="translate(320, 45)">
            <rect width="130" height="70" fill="#ffffff" stroke="#059669" strokeWidth="2" />
            <rect width="130" height="18" fill="#d1fae5" />
            <text x="8" y="13" fill="#065f46" fontSize="9" fontWeight="bold" fontFamily="monospace">
              PARTNER FLOW
            </text>
            <text x="8" y="36" fill="#0f172a" fontSize="10" fontWeight="bold">
              {nodes[1].label}
            </text>
            <text x="8" y="56" fill="#059669" fontSize="13" fontWeight="bold" fontFamily="monospace">
              {nodes[1].shockedValue} {nodes[1].unit}
            </text>
          </g>

          {/* Node 3: Net PnL */}
          <g transform="translate(540, 45)">
            <rect width="130" height="70" fill="#ffffff" stroke="#10b981" strokeWidth="2" />
            <rect width="130" height="18" fill="#ecfdf5" />
            <text x="8" y="13" fill="#047857" fontSize="9" fontWeight="bold" fontFamily="monospace">
              FINANCIAL
            </text>
            <text x="8" y="36" fill="#0f172a" fontSize="10" fontWeight="bold">
              {nodes[3].label}
            </text>
            <text x="8" y="56" fill="#047857" fontSize="13" fontWeight="bold" fontFamily="monospace">
              {nodes[3].shockedValue} {nodes[3].unit}
            </text>
          </g>

          {/* Node 4: Client Churn */}
          <g transform="translate(320, 150)">
            <rect width="130" height="60" fill="#ffffff" stroke="#d97706" strokeWidth="1.5" />
            <rect width="130" height="16" fill="#fef3c7" />
            <text x="8" y="12" fill="#92400e" fontSize="9" fontWeight="bold" fontFamily="monospace">
              CLIENT CHURN
            </text>
            <text x="8" y="32" fill="#0f172a" fontSize="10" fontWeight="bold">
              {nodes[2].label}
            </text>
            <text x="8" y="48" fill="#b45309" fontSize="11" fontWeight="bold" fontFamily="monospace">
              {nodes[2].shockedValue} {nodes[2].unit}
            </text>
          </g>
        </svg>
      </div>

      {/* Selected Edge Inspector Details */}
      {selectedEdge && (
        <div className="p-3 bg-slate-50 border border-slate-200 flex items-center justify-between text-xs font-mono">
          <div>
            <span className="font-bold text-slate-900">
              Edge: {selectedEdge.source} → {selectedEdge.target}
            </span>
            <div className="text-[11px] text-slate-600 mt-0.5">
              Placebo Refuter p={selectedEdge.placeboRefuterPValue} (threshold &gt; 0.05) | Confidence={Math.round(selectedEdge.confidence * 100)}%
            </div>
          </div>
          <span
            className={`px-2 py-0.5 font-bold text-[10px] ${
              selectedEdge.status === 'VERIFIED_CAUSAL'
                ? 'bg-[#EDF7ED] text-[#0D8050] border border-[#C3E6D0]'
                : 'bg-[#FAF5EC] text-[#A66321] border border-[#EAD8B5]'
            }`}
          >
            {selectedEdge.status}
          </span>
        </div>
      )}
    </div>
  );
}
