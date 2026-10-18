'use client';

/**
 * Tables and charts of an assistant answer. Every cell is a value a tool returned in the same turn; the model only named
 * the list. A missing value is a gap, never a zero, and each visual says where its data came from and as of when.
 */

import * as React from 'react';
import type { AnswerVisual, VisualCell, VisualColumn } from '../state/cockpit-types';
import { dateMs, formatAxisDate, formatText, formatTick, formatValue, niceTicks } from '../common/visual-format';

const SERIES_COLOURS = ['var(--color-cx-accent)', 'var(--color-cx-warn-solid)', 'var(--color-cx-ink-soft)'];
const NO_DATA = 'No data';

function cellText(value: VisualCell, column: VisualColumn): string {
  if (value === null || value === undefined) return '—';
  return typeof value === 'number' ? formatValue(value, column.unit) : formatText(value);
}

export function VisualTable({ visual }: { visual: AnswerVisual }) {
  return (
    <div className="max-h-64 overflow-auto">
      <table className="w-full border-collapse text-[11px] font-sans">
        <caption className="sr-only">{visual.label}</caption>
        <thead className="sticky top-0 bg-cx-sub">
          <tr>
            {visual.columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={`px-2 py-1 text-label font-medium text-cx-muted border-b border-cx-line whitespace-nowrap ${c.kind === 'number' ? 'text-right' : 'text-left'}`}
              >
                {c.label}
                {c.unit === 'USD' ? ' (USD)' : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visual.rows.map((row, i) => (
            <tr key={i} className="border-b border-cx-line-soft last:border-b-0 hover:bg-cx-hover">
              {visual.columns.map((c) => {
                const value = row[c.key];
                const missing = value === null || value === undefined;
                return (
                  <td
                    key={c.key}
                    title={missing ? NO_DATA : undefined}
                    className={`px-2 py-1 align-top ${c.kind === 'number' ? 'text-right font-mono tabular-nums text-cx-ink' : 'text-left text-cx-ink-soft min-w-[4rem] max-w-[9rem] break-words'} ${missing ? 'text-cx-faint' : ''}`}
                  >
                    {cellText(value, c)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const W = 360;
const H = 170;
const M = { left: 46, right: 10, top: 10, bottom: 24 };

interface Point {
  x: number;
  y: number | null;
  label: string;
}

function LineChart({ visual }: { visual: AnswerVisual }) {
  const plan = visual.chart!;
  const xs = visual.rows.map((r) => String(r[plan.x] ?? ''));
  const times = xs.map(dateMs);
  const timed = times.every((t) => t !== undefined);
  const x0 = timed ? Math.min(...(times as number[])) : 0;
  const x1 = timed ? Math.max(...(times as number[])) : Math.max(xs.length - 1, 1);
  const px = (i: number) => {
    const v = timed ? (times[i] as number) : i;
    return M.left + (x1 === x0 ? 0.5 : (v - x0) / (x1 - x0)) * (W - M.left - M.right);
  };
  const series = plan.y.map((key) => ({
    key,
    column: visual.columns.find((c) => c.key === key)!,
    points: visual.rows.map<Point>((r, i) => ({ x: px(i), y: typeof r[key] === 'number' ? (r[key] as number) : null, label: xs[i] })),
  }));
  const values = series.flatMap((s) => s.points.flatMap((p) => (p.y === null ? [] : [p.y])));
  if (values.length === 0) return <p className="px-2 py-3 text-label text-cx-muted">{NO_DATA}</p>;
  const hi = Math.max(...values);
  const lowest = Math.min(0, ...values);
  const ticks = niceTicks(lowest, hi === lowest ? lowest + 1 : hi, 4);
  const lo = ticks[0];
  const top = ticks[ticks.length - 1];
  const py = (v: number) => H - M.bottom - ((v - lo) / (top - lo || 1)) * (H - M.top - M.bottom);
  const dense = visual.rows.length > 31;
  // Labels sit at the start, middle and end of the axis. On a time axis the middle is the middle in time, not the middle
  // row: rows cluster, and a row-wise middle lands on top of the last label.
  const span = W - M.left - M.right;
  const axisLabels = (
    timed
      ? [0, 0.5, 1].map((f) => ({ x: M.left + f * span, text: formatAxisDate(new Date(x0 + f * (x1 - x0)).toISOString()), f }))
      : [0, Math.floor((xs.length - 1) / 2), xs.length - 1].map((i) => ({ x: px(i), text: xs[i].slice(0, 14), f: i === 0 ? 0 : i === xs.length - 1 ? 1 : 0.5 }))
  ).filter((label, i, all) => all.findIndex((l) => l.text === label.text) === i);
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`${visual.label}: ${series.map((s) => s.column.label).join(', ')} from ${formatAxisDate(xs[0])} to ${formatAxisDate(xs[xs.length - 1])}, ${visual.rows.length} points`}
      className="w-full h-auto"
    >
      {ticks.map((t) => (
        <g key={t}>
          <line x1={M.left} x2={W - M.right} y1={py(t)} y2={py(t)} stroke="var(--color-cx-line-soft)" strokeWidth={1} />
          <text x={M.left - 6} y={py(t) + 3} textAnchor="end" fontSize={9} fill="var(--color-cx-muted)">
            {formatTick(t, plan.unit)}
          </text>
        </g>
      ))}
      {axisLabels.map((label) => (
        <text key={label.f} x={label.x} y={H - 8} textAnchor={label.f === 0 ? 'start' : label.f === 1 ? 'end' : 'middle'} fontSize={9} fill="var(--color-cx-muted)">
          {label.text}
        </text>
      ))}
      {series.map((s, si) => {
        const colour = SERIES_COLOURS[si % SERIES_COLOURS.length];
        // a gap breaks the line: nothing is drawn between two points across a missing value
        const runs: Point[][] = [];
        s.points.forEach((p) => {
          if (p.y === null) runs.push([]);
          else if (runs.length === 0) runs.push([p]);
          else runs[runs.length - 1].push(p);
        });
        return (
          <g key={s.key}>
            {runs
              .filter((run) => run.length > 1)
              .map((run, ri) => (
                <polyline key={ri} fill="none" stroke={colour} strokeWidth={1.6} points={run.map((p) => `${p.x},${py(p.y as number)}`).join(' ')} />
              ))}
            {(!dense || s.points.every((p) => p.y === null)) &&
              s.points.map((p, pi) =>
                p.y === null ? null : (
                  <circle key={pi} cx={p.x} cy={py(p.y)} r={2.4} fill={colour}>
                    <title>{`${s.column.label} ${p.label}: ${formatValue(p.y, s.column.unit)}`}</title>
                  </circle>
                ),
              )}
          </g>
        );
      })}
    </svg>
  );
}

function BarChart({ visual }: { visual: AnswerVisual }) {
  const plan = visual.chart!;
  const column = visual.columns.find((c) => c.key === plan.y[0])!;
  const values = visual.rows.flatMap((r) => (typeof r[column.key] === 'number' ? [r[column.key] as number] : []));
  if (values.length === 0) return <p className="px-2 py-3 text-label text-cx-muted">{NO_DATA}</p>;
  const lo = Math.min(0, ...values);
  const hi = Math.max(0, ...values);
  const span = hi - lo || 1;
  const zero = ((0 - lo) / span) * 100;
  return (
    <ul role="img" aria-label={`${visual.label}: ${column.label} by ${plan.x}`} className="space-y-1 px-2 py-2">
      {visual.rows.map((row, i) => {
        const value = row[column.key];
        const n = typeof value === 'number' ? value : null;
        const width = n === null ? 0 : (Math.abs(n) / span) * 100;
        const left = n === null ? zero : n >= 0 ? zero : zero - width;
        return (
          <li key={i} className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-2 text-[11px]">
            <span className="truncate text-cx-ink-soft" title={String(row[plan.x] ?? '')}>
              {String(row[plan.x] ?? '')}
            </span>
            <span className="relative h-3 bg-cx-sub">
              {n !== null && (
                <span
                  className="absolute top-0 h-3"
                  style={{ left: `${left}%`, width: `${width}%`, background: SERIES_COLOURS[0] }}
                />
              )}
              {lo < 0 && <span className="absolute top-0 h-3 w-px bg-cx-ink-soft" style={{ left: `${zero}%` }} />}
            </span>
            <span className="font-mono tabular-nums text-cx-ink text-right" title={n === null ? NO_DATA : undefined}>
              {n === null ? '—' : formatValue(n, column.unit)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function Legend({ visual }: { visual: AnswerVisual }) {
  const plan = visual.chart!;
  if (plan.type !== 'line' || plan.y.length < 2) return null;
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-0.5 px-2 pb-1 text-label text-cx-muted">
      {plan.y.map((key, i) => (
        <li key={key} className="flex items-center gap-1">
          <span className="inline-block h-0.5 w-3" style={{ background: SERIES_COLOURS[i % SERIES_COLOURS.length] }} aria-hidden="true" />
          {visual.columns.find((c) => c.key === key)?.label ?? key}
        </li>
      ))}
    </ul>
  );
}

function asOfText(iso: string): string {
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(iso);
  return m ? `${m[1]} ${m[2]} UTC` : iso;
}

function VisualCard({ visual, answerText }: { visual: AnswerVisual; answerText: string }) {
  const isChart = visual.kind === 'chart' && visual.chart;
  return (
    <figure className="border border-cx-line bg-white" data-visual={visual.kind}>
      <div className="flex items-baseline justify-between gap-2 border-b border-cx-line-soft px-2 py-1">
        <span className="text-xs font-semibold text-cx-ink">{visual.label}</span>
        <span className="font-mono text-label text-cx-faint truncate" title={visual.source}>
          {visual.source}
        </span>
      </div>
      {isChart ? (
        <>
          <Legend visual={visual} />
          {visual.chart!.type === 'line' ? <LineChart visual={visual} /> : <BarChart visual={visual} />}
          <details className="border-t border-cx-line-soft">
            <summary className="cursor-pointer select-none px-2 py-1 text-label text-cx-accent">Data</summary>
            <VisualTable visual={visual} />
          </details>
        </>
      ) : (
        <VisualTable visual={visual} />
      )}
      <figcaption className="border-t border-cx-line-soft px-2 py-1 text-label text-cx-muted" title={visual.dataOrigin ? `Data origin: ${visual.dataOrigin}` : undefined}>
        {visual.citation ? `Source: ${visual.citation}` : 'Source: governed tool result'}
        {visual.asOf && !answerText.includes(asOfText(visual.asOf)) ? ` · as of ${asOfText(visual.asOf)}` : ''}
      </figcaption>
    </figure>
  );
}

/** `answerText` is the answer's own prose: a time it already states under the answer is not repeated in a card's caption. */
export function AnswerVisuals({ visuals, answerText = '' }: { visuals: AnswerVisual[]; answerText?: string }) {
  if (visuals.length === 0) return null;
  return (
    <div className="space-y-2.5">
      {visuals.map((v) => (
        <VisualCard key={`${v.kind}:${v.source}`} visual={v} answerText={answerText} />
      ))}
    </div>
  );
}
