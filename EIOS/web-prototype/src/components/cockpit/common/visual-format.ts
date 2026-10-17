/**
 * How a value from a tool result is written in a table or chart. The unit words and the shapes match the backend's
 * `render_figure` (assistant/assembly.py), so a cell reads as the same figure would in the sentences.
 */

const plain = (value: number): string => value.toLocaleString('en-US', { maximumFractionDigits: 6 });

/** A value with its unit: `$1,234`, `34.57%`, `16x`, `89`, `4 hours`. */
export function formatValue(value: number, unit?: string): string {
  switch (unit) {
    case 'USD':
      return `$${value.toLocaleString('en-US', Number.isInteger(value) ? { maximumFractionDigits: 0 } : { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    case 'percent':
      return `${plain(value)}%`;
    case 'multiplier':
    case 'x':
      return `${plain(value)}x`;
    case undefined:
    case 'ratio':
    case 'score':
    case 'count':
      return plain(value);
    default:
      return `${plain(value)} ${unit}`;
  }
}

const COMPACT = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

/** A short value for an axis tick: `$1.2K`, `35%`. */
export function formatTick(value: number, unit?: string): string {
  const body = COMPACT.format(value);
  if (unit === 'USD') return value < 0 ? `-$${COMPACT.format(-value)}` : `$${body}`;
  if (unit === 'percent') return `${body}%`;
  if (unit === 'multiplier' || unit === 'x') return `${body}x`;
  return body;
}

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/;

/** A date or timestamp the tool wrote, as `2026-08-14` or `2026-08-14 10:00` (UTC, as the tool gave it); any other text unchanged. */
export function formatText(value: string): string {
  const m = ISO_DATE.exec(value);
  if (!m) return value;
  return m[4] ? `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]}` : `${m[1]}-${m[2]}-${m[3]}`;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** `Aug 14` for an axis; the text itself when it is not a date. */
export function formatAxisDate(value: string): string {
  const m = ISO_DATE.exec(value);
  return m ? `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}` : value;
}

/** Epoch milliseconds of a tool's date or timestamp, or undefined when it is not one. */
export function dateMs(value: string): number | undefined {
  if (!ISO_DATE.test(value)) return undefined;
  const ms = Date.parse(value.length === 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(ms) ? undefined : ms;
}

/** Round tick values from at or below `lo` to at or above `hi`, about `count` of them, so the axis is exactly the ticks. */
export function niceTicks(lo: number, hi: number, count = 4): number[] {
  if (!(hi > lo)) return [lo];
  const rough = (hi - lo) / count;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= rough) ?? 10 * magnitude;
  const ticks: number[] = [];
  for (let t = Math.floor(lo / step) * step; ; t += step) {
    ticks.push(Number(t.toPrecision(12)));
    if (t >= hi - step * 1e-9) break;
  }
  return ticks;
}
