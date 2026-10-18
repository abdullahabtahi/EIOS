import { describe, it, expect } from 'vitest';
import { summarize, summarizeReference } from '@/components/cockpit/geo/geo-aggregates';
import { buildLayers, MIN_OFFSHORE_ENTITIES } from '@/components/cockpit/geo/geo-layers';
import { areaTier } from '@/components/cockpit/geo/geo-basis';
import { ARC_BUDGET, MAX_MISMATCH_PAIRS, drawnKinds, rankedCorridors, shownCorridors, shownPairs } from '@/components/cockpit/geo/geo-rank';
import type { FlowCorridor, GeoFlows } from '@/components/cockpit/geo/geo-types';
import type { LayerId } from '@/components/cockpit/geo/geo-types';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';

const ALL: ReadonlySet<LayerId> = new Set(['risk', 'offshore', 'corridors', 'mismatches']);

describe('summarize (engine flows)', () => {
  it('passes the engine exposure through and counts flagged accounts across pairs', () => {
    const s = summarize(FLOWS)!;
    expect(s.exposure).toEqual(FLOWS.exposure);
    expect(s.flaggedAccounts).toBe(25);
    expect(s.corridorVolumeUsd).toBe(1_400_000);
  });

  it('is null without flows, and reports no corridor volume (not zero) for an empty set', () => {
    expect(summarize(null)).toBeNull();
    expect(summarize({ ...FLOWS, corridors: [] })!.corridorVolumeUsd).toBeNull();
  });

  it('does not mutate its input', () => {
    const before = JSON.stringify(FLOWS);
    summarize(FLOWS);
    expect(JSON.stringify(FLOWS)).toBe(before);
  });
});

describe('summarizeReference', () => {
  it('counts FATF listings by list', () => {
    expect(summarizeReference(REFERENCE)?.fatf).toEqual({ call_for_action: 1, increased_monitoring: 1 });
  });

  it('is null when there is no reference layer: no data, not zero', () => {
    expect(summarizeReference(null)).toBeNull();
  });
});

describe('FATF area tier', () => {
  it('maps FATF lists to risk tiers and leaves unlisted countries unrated', () => {
    const by = Object.fromEntries(REFERENCE.countries.map((c) => [c.iso2, areaTier(c, 'fatf')]));
    expect(by).toMatchObject({ IR: 'high', KE: 'medium', BS: null, NO: null });
  });
});

describe('buildLayers', () => {
  const ids = (...args: Parameters<typeof buildLayers>) => buildLayers(...args).map((l) => l.id);

  it('builds one layer per visible lens with stable ids', () => {
    expect(ids(FLOWS, REFERENCE, ALL, null)).toEqual(['geo-risk', 'geo-offshore', 'geo-corridors', 'geo-mismatches']);
  });

  it('omits hidden lenses and returns nothing when none is visible', () => {
    expect(ids(FLOWS, REFERENCE, new Set<LayerId>(['corridors']), null)).toEqual(['geo-corridors']);
    expect(ids(FLOWS, REFERENCE, new Set<LayerId>(), null)).toEqual([]);
  });

  it('draws no flow lens without the reference layer, since it places the countries', () => {
    expect(ids(FLOWS, null, ALL, null)).toEqual([]);
  });

  it('draws only the reference lenses when the flows are absent', () => {
    expect(ids(null, REFERENCE, ALL, null)).toEqual(['geo-risk', 'geo-offshore']);
  });

  it('is deterministic and does not mutate its inputs', () => {
    const before = JSON.stringify([FLOWS, REFERENCE]);
    expect(ids(FLOWS, REFERENCE, ALL, null)).toEqual(ids(FLOWS, REFERENCE, ALL, null));
    expect(JSON.stringify([FLOWS, REFERENCE])).toBe(before);
  });

  it('feeds each layer exactly the data rows (no invented marks)', () => {
    const layers = buildLayers(FLOWS, REFERENCE, ALL, null);
    const rows = (id: string) => (layers.find((l) => l.id === id)!.props.data as unknown[]).length;
    expect(rows('geo-risk')).toBe(REFERENCE.countries.length);
    expect(rows('geo-offshore')).toBe(
      REFERENCE.countries.filter((c) => (c.entities_incorporated ?? 0) >= MIN_OFFSHORE_ENTITIES).length,
    );
    expect(rows('geo-corridors')).toBe(FLOWS.corridors.length);
    expect(rows('geo-mismatches')).toBe(FLOWS.mismatch_pairs.length);
  });

  it('skips a flow whose country the reference layer cannot place, instead of guessing a position', () => {
    const stray = { ...FLOWS, corridors: [...FLOWS.corridors, { origin: 'ZZ', destination: 'NO', volume_usd: 1, accounts: 1, events: 1, tier: null }] };
    const rows = (buildLayers(stray, REFERENCE, ALL, null).find((l) => l.id === 'geo-corridors')!.props.data as unknown[]).length;
    expect(rows).toBe(FLOWS.corridors.length);
  });
});

describe('which arcs are drawn', () => {
  const corridor = (i: number, tier: FlowCorridor['tier'], volume: number): FlowCorridor => ({
    origin: 'NO', destination: `D${i}`, volume_usd: volume, accounts: 1, events: 1, tier,
  });
  const many = {
    ...FLOWS,
    corridors: [
      ...Array.from({ length: 20 }, (_, i) => corridor(i, 'medium', 1_000 + i)),
      ...Array.from({ length: 6 }, (_, i) => corridor(100 + i, 'high', 10 + i)),
      ...Array.from({ length: 20 }, (_, i) => corridor(200 + i, 'low', 50_000 + i)),
    ],
    mismatch_pairs: Array.from({ length: 30 }, (_, i) => ({ ...FLOWS.mismatch_pairs[0], ip_country: `X${i}`, accounts: i + 1 })),
  };

  it('ranks high before medium before the rest, then by volume, whatever the volumes', () => {
    const tiers = rankedCorridors(many).map((c) => c.tier);
    expect(tiers.slice(0, 6)).toEqual(Array(6).fill('high'));
    expect(tiers.slice(6, 26)).toEqual(Array(20).fill('medium'));
    expect(tiers.slice(26)).toEqual(Array(20).fill('low'));
    const high = rankedCorridors(many).slice(0, 6).map((c) => c.volume_usd);
    expect(high).toEqual([...high].sort((a, b) => b - a));
  });

  it('gives each kind of arc its own budget, so medium corridors are drawn beside a crowd of high ones', () => {
    const shown = shownCorridors(many);
    const count = (tier: FlowCorridor['tier']) => shown.filter((c) => c.tier === tier).length;
    expect(count('high')).toBe(Math.min(6, ARC_BUDGET.high)); // all 6 high
    expect(count('medium')).toBe(ARC_BUDGET.medium);
    expect(count('low')).toBe(ARC_BUDGET.other);
    const crowd = { ...many, corridors: [...many.corridors, ...Array.from({ length: 30 }, (_, i) => corridor(300 + i, 'high', 5_000 + i))] };
    expect(shownCorridors(crowd).filter((c) => c.tier === 'high')).toHaveLength(ARC_BUDGET.high);
    expect(shownCorridors(crowd).filter((c) => c.tier === 'medium')).toHaveLength(ARC_BUDGET.medium);
  });

  it('takes the largest of each kind, and says which kinds are on the map', () => {
    const shown = shownCorridors(many);
    const lowShown = shown.filter((c) => c.tier === 'low').map((c) => c.volume_usd);
    const lowLeft = many.corridors.filter((c) => c.tier === 'low' && !shown.includes(c)).map((c) => c.volume_usd);
    expect(Math.min(...lowShown)).toBeGreaterThanOrEqual(Math.max(...lowLeft));
    expect([...drawnKinds(many)].sort()).toEqual(['high', 'medium', 'other']);
    expect([...drawnKinds({ ...FLOWS, corridors: [FLOWS.corridors[0]] })]).toEqual(['high']);
  });

  it('draws a corridor picked from the list even when it is not among the largest', () => {
    const hidden = many.corridors.find((c) => c.tier === 'low' && !shownCorridors(many).includes(c))!;
    const id = `${hidden.origin}>${hidden.destination}`;
    // Every synthetic destination needs a place on the map, or its arc is (rightly) skipped.
    const placed = {
      ...REFERENCE,
      countries: [
        ...REFERENCE.countries,
        ...many.corridors.map((c) => ({ ...REFERENCE.countries[0], iso2: c.destination, name: c.destination, position: [10, 10] as const })),
      ],
    };
    const rows = (sel: Parameters<typeof buildLayers>[3]) =>
      (buildLayers(many, placed, new Set<LayerId>(['corridors']), sel)[0].props.data as unknown[]).length;
    expect(rows({ kind: 'corridor', id })).toBe(rows(null) + 1);
  });

  it('draws the largest flagged pairs first, capped', () => {
    const shown = shownPairs(many);
    expect(shown).toHaveLength(MAX_MISMATCH_PAIRS);
    expect(shown[0].accounts).toBe(30);
  });

  it('never drops an unrated corridor silently into the elevated set', () => {
    const unrated = { ...FLOWS, corridors: FLOWS.corridors.map((c) => ({ ...c, tier: null })) };
    expect(shownCorridors(unrated).length).toBe(FLOWS.corridors.length);
    expect(rankedCorridors(unrated).every((c) => c.tier === null)).toBe(true);
  });

  it('does not mutate the flows it ranks', () => {
    const before = JSON.stringify(many);
    rankedCorridors(many);
    shownPairs(many);
    expect(JSON.stringify(many)).toBe(before);
  });
});

describe('focusOf', () => {
  it('opens on the volume-weighted centre of the corridor end countries', async () => {
    const { focusOf, REGION_ZOOM } = await import('@/components/cockpit/geo/geo-focus');
    const f = focusOf(FLOWS, REFERENCE)!;
    expect(f.zoom).toBe(REGION_ZOOM);
    const lngs = REFERENCE.countries.map((c) => c.position[0]);
    expect(f.center.lng).toBeGreaterThan(Math.min(...lngs));
    expect(f.center.lng).toBeLessThan(Math.max(...lngs));
  });

  it('is null without flows, without the reference layer, or when no country can be placed', async () => {
    const { focusOf } = await import('@/components/cockpit/geo/geo-focus');
    expect(focusOf(null, REFERENCE)).toBeNull();
    expect(focusOf(FLOWS, null)).toBeNull();
    expect(focusOf({ ...FLOWS, corridors: [{ ...FLOWS.corridors[0], origin: 'ZZ', destination: 'YY' }] }, REFERENCE)).toBeNull();
  });
});

describe('the corridor map reads as a network, not a knot', () => {
  const rowsOf = (flows: GeoFlows, selection: Parameters<typeof buildLayers>[3] = null) =>
    buildLayers(flows, REFERENCE, new Set<LayerId>(['corridors']), selection).find((l) => l.id === 'geo-corridors')!.props.data as unknown as {
      path: [number, number][];
      colors: number[][];
      width: number;
      ref: { kind: string; id: string };
    }[];
  const back = { origin: 'IR', destination: 'NO', volume_usd: 50_000, accounts: 2, events: 5, tier: 'high' as const };

  it('draws the two directions of one pair as one route, led by the bigger direction, wider for both together', () => {
    const merged = rowsOf({ ...FLOWS, corridors: [...FLOWS.corridors, back] });
    expect(merged).toHaveLength(FLOWS.corridors.length);
    const pair = merged.find((r) => r.ref.id === 'NO>IR')!;
    const alone = rowsOf(FLOWS).find((r) => r.ref.id === 'NO>IR')!;
    expect(pair.width).toBeGreaterThanOrEqual(alone.width);
    expect(merged.some((r) => r.ref.id === 'IR>NO')).toBe(false);
  });

  it('draws a curved path from the origin to the destination with direction in its colour', () => {
    const row = rowsOf(FLOWS).find((r) => r.ref.id === 'NO>IR')!;
    expect(row.path.length).toBeGreaterThan(8);
    expect(row.colors).toHaveLength(row.path.length);
    expect(row.colors[0][3]).toBeLessThan(row.colors[row.colors.length - 1][3]);
  });

  it('puts the picked country in focus and quiets the routes that do not touch it', () => {
    const tail = (rows: ReturnType<typeof rowsOf>, id: string) => rows.find((r) => r.ref.id === id)!.colors.at(-1)![3];
    const none = rowsOf(FLOWS, null);
    const focused = rowsOf(FLOWS, { kind: 'country', id: 'IR' });
    expect(tail(focused, 'NO>IR')).toBe(tail(none, 'NO>IR'));
    expect(tail(focused, 'KE>BS')).toBeLessThan(tail(none, 'KE>BS'));
  });

  it('reads either direction of a pair as the picked corridor', () => {
    const rows = rowsOf({ ...FLOWS, corridors: [...FLOWS.corridors, back] }, { kind: 'corridor', id: 'IR>NO' });
    const lead = rows.find((r) => r.ref.id === 'NO>IR')!;
    const other = rows.find((r) => r.ref.id === 'KE>BS')!;
    expect(lead.width).toBeGreaterThan(other.width);
    expect(lead.colors.at(-1)![3]).toBeGreaterThan(other.colors.at(-1)![3]);
  });

  it('marks a country that four or more routes meet as a hub, and no other', () => {
    const hubIds = (flows: GeoFlows) =>
      buildLayers(flows, REFERENCE, new Set<LayerId>(['corridors']), null).filter((l) => l.id === 'geo-hubs');
    expect(hubIds(FLOWS)).toHaveLength(0);
    const star = {
      ...FLOWS,
      corridors: ['NO', 'KE', 'PA', 'BS'].map((o) => ({ origin: o, destination: 'IR', volume_usd: 1000, accounts: 1, events: 1, tier: 'high' as const })),
    };
    const [hub] = hubIds(star);
    expect((hub.props.data as { iso2: string }[]).map((h) => h.iso2)).toEqual(['IR']);
  });
});

describe('map colours come from the design tokens', () => {
  it('uses the same values the stylesheet declares for state colour and ink', async () => {
    const { readFileSync } = await import('node:fs');
    const { join } = await import('node:path');
    const { GEO_TOKENS } = await import('@/components/cockpit/geo/geo-colors');
    const css = readFileSync(join(process.cwd(), 'src/app/globals.css'), 'utf8');
    for (const [name, hex] of Object.entries(GEO_TOKENS)) expect(css, name).toContain(`--color-${name}: ${hex};`);
  });
});
