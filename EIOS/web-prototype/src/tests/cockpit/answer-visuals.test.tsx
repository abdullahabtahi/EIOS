import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import React from 'react';
import { AnswerVisuals } from '@/components/cockpit/shell/answer-visuals';
import { ChatTurnView, type ChatTurn } from '@/components/cockpit/shell/chat-turn';
import { dateMs, formatAxisDate, formatText, formatTick, formatValue, niceTicks } from '@/components/cockpit/common/visual-format';
import { normalizeVisuals } from '@/lib/server/normalize-visuals';
import type { AnswerVisual, CopilotQueryResponse } from '@/components/cockpit/state/cockpit-types';

const timeline = {
  kind: 'chart',
  source: 'get_activity_timeline.events',
  label: 'Events',
  columns: [
    { key: 'at', label: 'At', kind: 'text' },
    { key: 'kind', label: 'Kind', kind: 'text' },
    { key: 'event_amount_usd', label: 'Event amount', kind: 'number', unit: 'USD' },
  ],
  rows: [
    { at: '2026-08-14T10:00:00+00:00', kind: 'KYC_APPROVED', event_amount_usd: null },
    { at: '2026-08-20T09:30:00+00:00', kind: 'DEPOSIT', event_amount_usd: 4000 },
    { at: '2026-08-27T09:30:00+00:00', kind: 'DEPOSIT', event_amount_usd: 8000.5 },
  ],
  chart: { type: 'line', x: 'at', y: ['event_amount_usd'], unit: 'USD' },
  as_of: '2026-10-17T08:30:21.056328Z',
  data_origin: 'engine',
  citation: 'warm.activity',
};

const attribution = {
  kind: 'chart',
  source: 'run_what_if.attribution',
  label: 'Attribution',
  columns: [
    { key: 'driver', label: 'Driver', kind: 'text' },
    { key: 'contribution_pct', label: 'Contribution', kind: 'number', unit: 'percent' },
  ],
  rows: [
    { driver: 'Competitor Spread Shock', contribution_pct: 34.57 },
    { driver: 'Volume Elasticity', contribution_pct: 65.43 },
  ],
  chart: { type: 'bar', x: 'driver', y: ['contribution_pct'], unit: 'percent' },
  as_of: '2026-10-17T08:30:21Z',
  data_origin: 'engine',
  citation: 'exec.what_if',
};

const table = { ...timeline, kind: 'table', chart: undefined };

describe('normalizeVisuals', () => {
  it('maps a chart and a table, keeping the tool values as they were', () => {
    const [chart, plain] = normalizeVisuals([timeline, table]);
    expect(chart.kind).toBe('chart');
    expect(chart.chart).toEqual({ type: 'line', x: 'at', y: ['event_amount_usd'], unit: 'USD' });
    expect(chart.rows[2].event_amount_usd).toBe(8000.5);
    expect(chart.rows[0].event_amount_usd).toBeNull(); // a gap stays a gap, never zero
    expect(chart.asOf).toBe('2026-10-17T08:30:21.056328Z');
    expect(chart.dataOrigin).toBe('engine');
    expect(plain.chart).toBeUndefined();
  });

  it('drops what the browser could not draw honestly', () => {
    expect(normalizeVisuals('nope')).toEqual([]);
    expect(normalizeVisuals([{ ...timeline, kind: 'pie' }])).toEqual([]);
    expect(normalizeVisuals([{ ...timeline, columns: [] }])).toEqual([]);
    expect(normalizeVisuals([{ ...timeline, rows: [] }])).toEqual([]);
    expect(normalizeVisuals([{ ...timeline, chart: { type: 'line', x: 'at', y: ['missing'] } }])).toEqual([]);
    expect(normalizeVisuals([{ ...timeline, chart: undefined }])).toEqual([]); // a chart with no plan
    expect(normalizeVisuals([{ ...timeline, chart: { type: 'line', x: 'event_amount_usd', y: ['event_amount_usd'] } }])).toEqual([]);
  });

  it('turns a cell that is not a string or a finite number into a gap, and ignores keys that are not columns', () => {
    const [v] = normalizeVisuals([
      { ...timeline, rows: [{ at: '2026-08-14', kind: 7, event_amount_usd: Number.NaN, extra: 'x' }, { at: '2026-08-15', kind: 'A', event_amount_usd: '12' }] },
    ]);
    expect(v.rows[0]).toEqual({ at: '2026-08-14', kind: null, event_amount_usd: null });
    expect(v.rows[1].event_amount_usd).toBeNull(); // a number sent as text is not trusted as a number
  });

  it('keeps at most a hundred rows and six columns', () => {
    const columns = Array.from({ length: 9 }, (_, i) => ({ key: `c${i}`, label: `C${i}`, kind: 'number' }));
    const rows = Array.from({ length: 150 }, () => Object.fromEntries(columns.map((c) => [c.key, 1])));
    const [v] = normalizeVisuals([{ kind: 'table', source: 't.rows', label: 'R', columns, rows, as_of: '', citation: '' }]);
    expect(v.columns).toHaveLength(6);
    expect(v.rows).toHaveLength(100);
  });
});

describe('visual formatting', () => {
  it('writes a value the way the backend writes the same figure', () => {
    expect(formatValue(1234, 'USD')).toBe('$1,234');
    expect(formatValue(8000.5, 'USD')).toBe('$8,000.50');
    expect(formatValue(34.57, 'percent')).toBe('34.57%');
    expect(formatValue(16, 'multiplier')).toBe('16x');
    expect(formatValue(89, 'score')).toBe('89');
    expect(formatValue(4, 'hours')).toBe('4 hours');
    expect(formatValue(1600)).toBe('1,600');
  });

  it('shortens axis ticks and dates', () => {
    expect(formatTick(1200, 'USD')).toBe('$1.2K');
    expect(formatTick(35, 'percent')).toBe('35%');
    expect(formatText('2026-08-14T10:00:00+00:00')).toBe('2026-08-14 10:00');
    expect(formatText('KYC_APPROVED')).toBe('KYC_APPROVED');
    expect(formatAxisDate('2026-08-14T10:00:00+00:00')).toBe('Aug 14');
    expect(dateMs('2026-08-14')).toBe(Date.UTC(2026, 7, 14));
    expect(dateMs('not a date')).toBeUndefined();
  });

  it('picks round ticks that cover the range', () => {
    const ticks = niceTicks(0, 8000.5, 4);
    expect(ticks[0]).toBe(0);
    expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(8000);
    expect(niceTicks(5, 5)).toEqual([5]);
  });
});

const visuals = (...raw: unknown[]): AnswerVisual[] => normalizeVisuals(raw);

describe('AnswerVisuals', () => {
  it('renders nothing for an answer with no visual', () => {
    const { container } = render(<AnswerVisuals visuals={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('draws a table with units, right-aligned numbers and a gap where the tool had no value', () => {
    render(<AnswerVisuals visuals={visuals(table)} />);
    const grid = screen.getByRole('table', { name: 'Events' });
    expect(within(grid).getByText('$4,000')).toBeInTheDocument();
    expect(within(grid).getByText('$8,000.50')).toBeInTheDocument();
    expect(within(grid).getByText('2026-08-20 09:30')).toBeInTheDocument();
    const gap = within(grid).getByTitle('No data');
    expect(gap).toHaveTextContent('—');
    expect(within(grid).queryByText('$0')).toBeNull(); // a missing value is never shown as zero
  });

  it('says where the data came from and as of when', () => {
    render(<AnswerVisuals visuals={visuals(table)} />);
    const caption = screen.getByText(/Source: warm\.activity/);
    expect(caption).toHaveTextContent('as of 2026-10-17 08:30 UTC');
    expect(caption).toHaveAttribute('title', 'Data origin: engine');
    expect(screen.getByTitle('get_activity_timeline.events')).toBeInTheDocument();
  });

  it('draws a line chart that names what it plots, with the data one click away', () => {
    render(<AnswerVisuals visuals={visuals(timeline)} />);
    const chart = screen.getByRole('img', { name: /Events: Event amount from Aug 14 to Aug 27, 3 points/ });
    expect(chart.querySelectorAll('circle')).toHaveLength(2); // two real points; the missing one is not drawn
    expect(chart.querySelectorAll('polyline')).toHaveLength(1);
    expect(screen.getByText('Data')).toBeInTheDocument();
  });

  it('puts the axis labels at the start, middle and end of the time span, so clustered rows cannot overlap them', () => {
    const clustered = {
      ...timeline,
      rows: [
        { at: '2026-08-14T10:00:00+00:00', kind: 'A', event_amount_usd: 1 },
        { at: '2026-10-11T09:00:00+00:00', kind: 'B', event_amount_usd: 2 },
        { at: '2026-10-12T09:00:00+00:00', kind: 'C', event_amount_usd: 3 },
      ],
    };
    render(<AnswerVisuals visuals={visuals(clustered)} />);
    const labels = [...screen.getByRole('img', { name: /Events/ }).querySelectorAll('text')]
      .map((t) => t.textContent)
      .filter((t): t is string => /^[A-Z][a-z]{2} \d+$/.test(t ?? ''));
    expect(labels).toEqual(['Aug 14', 'Sep 12', 'Oct 12']); // not 'Oct 11' beside 'Oct 12'
  });

  it('draws bars with a value on each row', () => {
    render(<AnswerVisuals visuals={visuals(attribution)} />);
    const bars = screen.getByRole('img', { name: /Attribution: Contribution by driver/ });
    expect(within(bars).getByText('Competitor Spread Shock')).toBeInTheDocument();
    expect(within(bars).getByText('34.57%')).toBeInTheDocument();
    expect(within(bars).getByText('65.43%')).toBeInTheDocument();
  });

  it('has a chart with nothing to plot say so instead of drawing an empty frame', () => {
    const empty = { ...timeline, rows: timeline.rows.map((r) => ({ ...r, event_amount_usd: null })) };
    render(<AnswerVisuals visuals={visuals(empty)} />);
    expect(screen.getAllByText('No data').length).toBeGreaterThan(0);
  });
});

describe('a chat turn with a visual', () => {
  const response = (extra: Partial<CopilotQueryResponse>): CopilotQueryResponse => ({
    queryId: 'q1',
    naturalLanguageQuery: 'chart it',
    responseMarkdown: 'Activity picked up late in the window.',
    citedMetrics: [],
    assistantStatus: 'ASSEMBLED',
    blocked: false,
    steps: [],
    proposals: [],
    timestamp: '2026-10-17T08:31:00Z',
    ...extra,
  });
  const turn = (r: CopilotQueryResponse): ChatTurn => ({ kind: 'turn', id: 't1', query: 'chart it', timestamp: r.timestamp, entityId: null, response: r });

  it('shows the chart under the sentences', () => {
    render(<ChatTurnView turn={turn(response({ visuals: visuals(timeline) }))} proposalStates={{}} onStage={() => {}} onShowInDossier={() => {}} />);
    expect(screen.getByText('Activity picked up late in the window.')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Events: Event amount/ })).toBeInTheDocument();
  });

  it('shows nothing extra for an answer without visuals', () => {
    render(<ChatTurnView turn={turn(response({}))} proposalStates={{}} onStage={() => {}} onShowInDossier={() => {}} />);
    expect(document.querySelector('[data-visual]')).toBeNull();
  });
});

describe('AnswerVisuals caption', () => {
  it('does not repeat a time the answer already states', () => {
    const withAsOf = { ...table, as_of: '2026-10-14T08:00:00Z' };
    const { rerender } = render(<AnswerVisuals visuals={visuals(withAsOf)} />);
    expect(screen.getByText(/as of 2026-10-14 08:00 UTC/)).toBeTruthy();
    rerender(<AnswerVisuals visuals={visuals(withAsOf)} answerText="Done.\n\n_as of 2026-10-14 08:00 UTC._" />);
    expect(screen.queryByText(/as of 2026-10-14 08:00 UTC/)).toBeNull();
  });
});
