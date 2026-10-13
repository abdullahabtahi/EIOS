import { describe, it, expect } from 'vitest';
import { formatAge, countBySeverity } from '@/components/cockpit/state/triage-meta';
import type { TriageItem } from '@/components/cockpit/state/cockpit-types';

const AS_OF = '2026-10-13T12:00:00.000Z';

describe('formatAge (relative to the data as-of time, never wall clock)', () => {
  it.each([
    ['2026-10-13T11:59:40.000Z', '<1m'],
    ['2026-10-13T11:46:00.000Z', '14m'],
    ['2026-10-13T09:00:00.000Z', '3h'],
    ['2026-10-11T12:00:00.000Z', '2d'],
  ])('%s -> %s', (ts, expected) => {
    expect(formatAge(ts, AS_OF)).toBe(expected);
  });

  it('never goes negative when an item is stamped after the as-of time', () => {
    expect(formatAge('2026-10-13T12:30:00.000Z', AS_OF)).toBe('<1m');
  });

  it('shows an em dash for unparseable input rather than inventing an age', () => {
    expect(formatAge('not-a-date', AS_OF)).toBe('—');
    expect(formatAge('2026-10-13T11:00:00Z', undefined)).toBe('—');
  });
});

describe('countBySeverity', () => {
  const mk = (severity: TriageItem['severity']): TriageItem => ({
    id: severity + Math.random(), role: 'executive', title: 't', subtitle: 's', entityId: 'e', entityType: 'ACCOUNT',
    priorityScore: 0.5, severity, status: 'OPEN', timestamp: AS_OF, tags: [], metricsSummary: {},
  });
  it('counts per severity plus ALL, ignoring INFO in the pills', () => {
    const counts = countBySeverity([mk('CRITICAL'), mk('CRITICAL'), mk('HIGH'), mk('LOW'), mk('INFO')]);
    expect(counts).toEqual({ ALL: 5, CRITICAL: 2, HIGH: 1, MEDIUM: 0, LOW: 1 });
  });
});
