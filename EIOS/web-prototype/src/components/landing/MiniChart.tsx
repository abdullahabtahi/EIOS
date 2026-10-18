import React from "react";
import type { Chart, Mark } from "./data/charts";

const pct = (v: number, min: number, max: number): number => ((v - min) / (max - min)) * 100;

/** Label sits above for the reference or earlier value, below for the measured one, so close marks never collide. */
function placement(tone: Mark["tone"]): "up" | "down" {
  return tone === "main" ? "down" : "up";
}

function anchor(p: number): "start" | "mid" | "end" {
  if (p > 78) return "end";
  if (p < 14) return "start";
  return "mid";
}

function TrackChart({ chart }: { chart: Extract<Chart, { kind: "track" }> }) {
  const at = (v: number) => pct(v, chart.min, chart.max);
  const [a, b] = chart.span ?? [];
  const lo = a !== undefined && b !== undefined ? Math.min(at(chart.marks[a].at), at(chart.marks[b].at)) : null;
  const hi = a !== undefined && b !== undefined ? Math.max(at(chart.marks[a].at), at(chart.marks[b].at)) : null;
  return (
    <div className="fde-mc fde-mc-track">
      <div className="fde-mc-rail">
        {chart.ticks.map((t) => (
          <span key={t} className="fde-mc-tick" style={{ left: `${at(t)}%` }}>
            <i />
          </span>
        ))}
        {lo !== null && hi !== null && <span className="fde-mc-span" style={{ left: `${lo}%`, width: `${hi - lo}%` }} />}
        {chart.marks.map((m) => {
          const p = at(m.at);
          return (
            <span key={m.label} className={`fde-mc-mark is-${m.tone}`} style={{ left: `${p}%` }}>
              <i className="fde-mc-dot" />
              <em className={`fde-mc-label is-${placement(m.tone)} is-${anchor(p)}`}>{m.label}</em>
            </span>
          );
        })}
      </div>
      <p className="fde-mc-unit">{chart.unit}</p>
    </div>
  );
}

export function MiniChart({ chart }: { chart: Chart }) {
  if (chart.kind === "fill") {
    const p = pct(chart.value, 0, chart.of);
    return (
      <div className="fde-mc fde-mc-fill">
        <div className="fde-mc-bar">
          <span style={{ width: `${p}%` }} />
        </div>
        <p className="fde-mc-unit">
          {chart.label}, of {chart.of}
          {chart.unit}
        </p>
      </div>
    );
  }
  if (chart.kind === "units") {
    return (
      <div className="fde-mc fde-mc-units">
        <div className="fde-mc-cells" style={{ gridTemplateColumns: `repeat(${Math.min(chart.total, 15)}, 1fr)` }}>
          {Array.from({ length: chart.total }, (_, i) => (
            <span key={i} className={i < chart.filled ? "is-on" : undefined} />
          ))}
        </div>
        <p className="fde-mc-unit">
          {chart.filled} of {chart.total} {chart.label}
        </p>
      </div>
    );
  }
  return <TrackChart chart={chart} />;
}
