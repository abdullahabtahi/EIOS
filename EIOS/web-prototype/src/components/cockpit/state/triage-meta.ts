/**
 * Pure helpers for triage queue context.
 * Ages are measured against the data's own as-of time (not the wall clock), so a
 * replayed or cached snapshot never shows an age that the data cannot support.
 */

import type { SeverityLevel, TriageItem } from './cockpit-types';

const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export function formatAge(timestamp: string, asOf: string | undefined): string {
  if (!asOf) return '—';
  const from = Date.parse(timestamp);
  const to = Date.parse(asOf);
  if (Number.isNaN(from) || Number.isNaN(to)) return '—';
  const delta = Math.max(0, to - from);
  if (delta < MINUTE_MS) return '<1m';
  if (delta < HOUR_MS) return `${Math.floor(delta / MINUTE_MS)}m`;
  if (delta < DAY_MS) return `${Math.floor(delta / HOUR_MS)}h`;
  return `${Math.floor(delta / DAY_MS)}d`;
}

export type SeverityCounts = Record<'ALL' | Exclude<SeverityLevel, 'INFO'>, number>;

export function countBySeverity(items: readonly TriageItem[]): SeverityCounts {
  const counts: SeverityCounts = { ALL: items.length, CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  for (const item of items) {
    if (item.severity !== 'INFO') counts[item.severity] += 1;
  }
  return counts;
}
