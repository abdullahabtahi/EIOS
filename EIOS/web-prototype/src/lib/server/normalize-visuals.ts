/**
 * The tables and charts of an assistant answer, from the backend's snake_case to the cockpit's shape.
 *
 * The backend has already checked that every row came from a tool result of the same turn. This only makes sure the
 * browser never draws something it cannot read: a visual with an unknown kind, no columns, or a chart that points at a
 * column it does not have is dropped whole, and a cell that is not a string or a finite number becomes a gap (`null`).
 */
import type {
  AnswerVisual,
  DataOrigin,
  VisualCell,
  VisualChartPlan,
  VisualColumn,
} from '@/components/cockpit/state/cockpit-types';
import { dataOriginOf } from '@/lib/server/normalize';

type Raw = Record<string, unknown>;

const MAX_ROWS = 100;
const MAX_COLUMNS = 6;
const KEY = /^[A-Za-z0-9_]{1,64}$/;

const text = (value: unknown): string => (typeof value === 'string' ? value : '');
const record = (value: unknown): Raw | undefined =>
  value && typeof value === 'object' && !Array.isArray(value) ? (value as Raw) : undefined;

function column(raw: unknown): VisualColumn | undefined {
  const r = record(raw);
  if (!r || !KEY.test(text(r.key)) || (r.kind !== 'text' && r.kind !== 'number')) return undefined;
  const unit = text(r.unit);
  return { key: text(r.key), label: text(r.label) || text(r.key), kind: r.kind, ...(unit ? { unit } : {}) };
}

function cell(value: unknown, kind: 'text' | 'number'): VisualCell {
  if (kind === 'number') return typeof value === 'number' && Number.isFinite(value) ? value : null;
  return typeof value === 'string' ? value : null;
}

function plan(raw: unknown, columns: VisualColumn[]): VisualChartPlan | undefined {
  const r = record(raw);
  if (!r || (r.type !== 'line' && r.type !== 'bar') || !Array.isArray(r.y)) return undefined;
  const x = columns.find((c) => c.key === r.x && c.kind === 'text');
  const y = r.y.filter((k): k is string => typeof k === 'string' && columns.some((c) => c.key === k && c.kind === 'number'));
  if (!x || y.length === 0 || y.length !== r.y.length) return undefined;
  const unit = text(r.unit);
  return { type: r.type, x: x.key, y, ...(unit ? { unit } : {}) };
}

function visual(raw: unknown): AnswerVisual | undefined {
  const r = record(raw);
  if (!r || (r.kind !== 'table' && r.kind !== 'chart') || !text(r.source) || !Array.isArray(r.columns) || !Array.isArray(r.rows)) {
    return undefined;
  }
  const columns = r.columns.slice(0, MAX_COLUMNS).map(column);
  if (columns.length === 0 || columns.some((c) => c === undefined)) return undefined;
  const cols = columns as VisualColumn[];
  const rows = r.rows.slice(0, MAX_ROWS).map((row) => {
    const source = record(row) ?? {};
    return Object.fromEntries(cols.map((c) => [c.key, cell(source[c.key], c.kind)]));
  });
  if (rows.length === 0) return undefined;
  const chart = r.kind === 'chart' ? plan(r.chart, cols) : undefined;
  if (r.kind === 'chart' && !chart) return undefined;
  const origin: DataOrigin | undefined = dataOriginOf(r.data_origin);
  return {
    kind: r.kind,
    source: text(r.source),
    label: text(r.label) || text(r.source),
    columns: cols,
    rows,
    ...(chart ? { chart } : {}),
    asOf: text(r.as_of),
    dataOrigin: origin,
    citation: text(r.citation),
  };
}

export function normalizeVisuals(raw: unknown): AnswerVisual[] {
  if (!Array.isArray(raw)) return [];
  return raw.flatMap((item) => {
    const v = visual(item);
    return v ? [v] : [];
  });
}
