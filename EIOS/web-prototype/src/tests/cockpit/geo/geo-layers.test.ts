import { describe, it, expect } from 'vitest';
import { summarize, summarizeReference } from '@/components/cockpit/geo/geo-aggregates';
import { buildLayers, shownCorridors, shownPairs, tierOf, MAX_MISMATCH_PAIRS, MAX_PLAIN_CORRIDORS, MIN_OFFSHORE_ENTITIES } from '@/components/cockpit/geo/geo-layers';
import type { LayerId } from '@/components/cockpit/geo/geo-types';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';

const ALL: ReadonlySet<LayerId> = new Set(['risk', 'offshore', 'corridors', 'mismatches']);

describe('summarize (engine flows)', () => {
  it('ranks corridors by volume, descending, capped at n', () => {
    const top = summarize(FLOWS, 2)!.topCorridors;
    expect(top.map((c) => c.volume_usd)).toEqual([900_000, 400_000]);
  });

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
  it('counts FATF listings by list and ranks offshore centres by incorporated entities', () => {
    const r = summarizeReference(REFERENCE, 2);
    expect(r?.fatf).toEqual({ call_for_action: 1, increased_monitoring: 1 });
    expect(r?.topOffshore.map((c) => c.iso2)).toEqual(['BS', 'PA']);
  });

  it('is null when there is no reference layer: no data, not zero', () => {
    expect(summarizeReference(null)).toBeNull();
  });
});

describe('tierOf', () => {
  it('maps FATF lists to risk tiers and leaves unlisted countries unrated', () => {
    const by = Object.fromEntries(REFERENCE.countries.map((c) => [c.iso2, tierOf(c)]));
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
  const many = {
    ...FLOWS,
    corridors: [
      ...FLOWS.corridors,
      ...Array.from({ length: 20 }, (_, i) => ({ origin: 'NO', destination: 'BS', volume_usd: 10 + i, accounts: 1, events: 1, tier: 'low' as const })),
    ],
    mismatch_pairs: Array.from({ length: 30 }, (_, i) => ({ ...FLOWS.mismatch_pairs[0], ip_country: `X${i}`, accounts: i + 1 })),
  };

  it('always draws every elevated corridor, plus only the largest of the rest', () => {
    const shown = shownCorridors(many);
    const elevated = many.corridors.filter((c) => c.tier === 'high' || c.tier === 'medium');
    expect(elevated.every((c) => shown.includes(c))).toBe(true);
    expect(shown.length).toBe(elevated.length + MAX_PLAIN_CORRIDORS);
    const plain = shown.filter((c) => c.tier === 'low').map((c) => c.volume_usd);
    expect(Math.min(...plain)).toBeGreaterThanOrEqual(Math.max(...many.corridors.filter((c) => c.tier === 'low' && !shown.includes(c)).map((c) => c.volume_usd)));
  });

  it('draws the largest flagged pairs first, capped', () => {
    const shown = shownPairs(many);
    expect(shown).toHaveLength(MAX_MISMATCH_PAIRS);
    expect(shown[0].accounts).toBe(30);
  });

  it('never drops an unrated corridor silently into the elevated set', () => {
    const unrated = { ...FLOWS, corridors: FLOWS.corridors.map((c) => ({ ...c, tier: null })) };
    expect(shownCorridors(unrated).length).toBe(FLOWS.corridors.length);
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
