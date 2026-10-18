"use client";

import React, { useId, useState } from "react";
import { ATTRIBUTION, CAUSAL_EDGES, CAUSAL_NODES, WHAT_IF } from "../data/causal";

/** Screen positions of the five fitted nodes: a left-to-right causal chain with the tested-and-rejected control below. */
const POS: Readonly<Record<string, { x: number; y: number }>> = {
  competitor_payout_rate: { x: 66, y: 60 },
  avg_spread_pip: { x: 66, y: 226 },
  partner_churn_rate: { x: 290, y: 143 },
  ftd_count_28d: { x: 500, y: 143 },
  net_revenue_usd: { x: 700, y: 143 },
};

const SHORT: Readonly<Record<string, string>> = {
  competitor_payout_rate: "Competitor payout",
  avg_spread_pip: "Average spread",
  partner_churn_rate: "Partner churn",
  ftd_count_28d: "First deposits",
  net_revenue_usd: "Net revenue",
};

const usd = (n: number): string =>
  `${n < 0 ? "−" : "+"}$${Math.abs(n).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
const pct = (n: number): string => `${n > 0 ? "+" : n < 0 ? "−" : ""}${Math.abs(n).toFixed(1)}%`;

export function CausalWhatIf() {
  const zero = WHAT_IF.findIndex((s) => s.pct === 0);
  const [idx, setIdx] = useState(zero + 3);
  const sliderId = useId();
  const s = WHAT_IF[idx];
  const delta: Readonly<Record<string, string | null>> = {
    competitor_payout_rate: pct(s.pct),
    partner_churn_rate: pct(s.churn),
    ftd_count_28d: pct(s.ftd),
    net_revenue_usd: usd(s.revenue),
    avg_spread_pip: null,
  };
  const regions = Object.entries(ATTRIBUTION);

  return (
    <figure className="fde-viz" data-causal={s.causal}>
      <svg viewBox="0 0 760 290" className="fde-dag" role="img" aria-label="Fitted causal graph: competitor payout drives partner churn, which drives first deposits and net revenue; the average spread link was tested and holds only as correlation.">
        <defs>
          <marker id="fde-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
            <path d="M0 1L9 5L0 9" className="fde-dag-head" />
          </marker>
        </defs>
        {CAUSAL_EDGES.map((e) => {
          const a = POS[e.from];
          const b = POS[e.to];
          return (
            <g key={`${e.from}-${e.to}`} className={e.verified ? "fde-dag-edge is-causal" : "fde-dag-edge is-corr"}>
              <path d={`M${a.x + 56} ${a.y}L${b.x - 58} ${b.y}`} markerEnd="url(#fde-arrow)" />
              <text
                x={(a.x + b.x) / 2 + (a.y === b.y ? 0 : 24)}
                y={(a.y + b.y) / 2 + (a.y === b.y ? 44 : a.y < b.y ? -30 : 34)}
                textAnchor={a.y === b.y ? "middle" : "start"}
              >
                {e.verified ? `p ${e.placeboP.toFixed(2)} · conf ${e.confidence.toFixed(2)}` : "correlation only"}
              </text>
            </g>
          );
        })}
        {CAUSAL_NODES.map((n) => {
          const p = POS[n.id];
          return (
            <g key={n.id} className="fde-dag-node">
              <rect x={p.x - 54} y={p.y - 26} width={108} height={52} />
              <text x={p.x} y={p.y - 4} textAnchor="middle" className="fde-dag-name">{SHORT[n.id]}</text>
              {delta[n.id] && (
                <text x={p.x} y={p.y + 14} textAnchor="middle" className="fde-dag-delta">{delta[n.id]}</text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="fde-whatif">
        <label htmlFor={sliderId} className="fde-whatif-label">
          Shock: competitor raises its payout by <strong>{pct(s.pct)}</strong>
        </label>
        <input
          id={sliderId}
          type="range"
          min={0}
          max={WHAT_IF.length - 1}
          step={1}
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
          className="fde-range"
          aria-valuetext={`${pct(s.pct)} payout change`}
        />
        <div className="fde-whatif-out" aria-live="polite">
          <p>
            Revenue {usd(s.revenue)} <span className="fde-whatif-ci">90% band {usd(s.ci[0])} to {usd(s.ci[1])}</span>
          </p>
          <p className={`fde-verdict${s.causal ? "" : " is-open"}`}>
            {s.causal ? "Verified causal inside the history" : "Correlation only: this shock is outside anything the history saw"}
          </p>
        </div>
        <div className="fde-attr" aria-label="Where the impact lands, by partner region">
          {regions.map(([region, share]) => (
            <span key={region} style={{ flexGrow: share }} className="fde-attr-seg">
              <span className="fde-attr-name">{region}</span>
              <span className="fde-attr-val">{share.toFixed(2)}%</span>
            </span>
          ))}
        </div>
      </div>
      <figcaption className="fde-viz-cap">
        The executive engine&apos;s fitted graph and what-if, sampled from the running engine over the seeded executive world.
        Regional attribution sums to 100.00%.
      </figcaption>
    </figure>
  );
}
