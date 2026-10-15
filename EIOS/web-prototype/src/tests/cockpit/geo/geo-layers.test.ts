import { describe, it, expect } from 'vitest';
import { GEO_FIXTURE } from '@/components/cockpit/geo/geo-fixture';
import { summarize, summarizeReference } from '@/components/cockpit/geo/geo-aggregates';
import { buildLayers, tierOf, MIN_OFFSHORE_ENTITIES } from '@/components/cockpit/geo/geo-layers';
import type { LayerId } from '@/components/cockpit/geo/geo-types';
import { REFERENCE } from './reference-fixture';

const ALL: ReadonlySet<LayerId> = new Set(['risk', 'offshore', 'corridors', 'mismatches']);

describe('geo fixture integrity', () => {
  it('every corridor and mismatch references a known jurisdiction', () => {
    const codes = new Set(GEO_FIXTURE.jurisdictions.map((j) => j.code));
    for (const c of GEO_FIXTURE.corridors) {
      expect(codes.has(c.origin)).toBe(true);
      expect(codes.has(c.destination)).toBe(true);
    }
    for (const m of GEO_FIXTURE.mismatches) {
      expect(codes.has(m.kycCountry)).toBe(true);
      expect(codes.has(m.ipCountry)).toBe(true);
      expect(m.kycCountry).not.toBe(m.ipCountry);
    }
  });

  it('carries provenance (source and as-of) so nothing is drawn without a stated origin', () => {
    expect(GEO_FIXTURE.source).toBeTruthy();
    expect(GEO_FIXTURE.asOf).toMatch(/^\d{4}-\d{2}-\d{2}/);
  });
});

describe('summarize', () => {
  it('splits corridor volume by tier and the parts sum to the total', () => {
    const s = summarize(GEO_FIXTURE);
    const parts = s.volumeByTier.low + s.volumeByTier.medium + s.volumeByTier.high;
    expect(parts).toBe(s.corridorVolumeUsd);
    expect(s.corridorVolumeUsd).toBe(GEO_FIXTURE.corridors.reduce((t, c) => t + c.volumeUsd, 0));
  });

  it('ranks top corridors by volume, descending, capped at n', () => {
    const top = summarize(GEO_FIXTURE, 3).topCorridors;
    expect(top).toHaveLength(3);
    expect(top[0].volumeUsd).toBeGreaterThanOrEqual(top[1].volumeUsd);
    expect(top[1].volumeUsd).toBeGreaterThanOrEqual(top[2].volumeUsd);
  });

  it('counts IP-versus-KYC mismatches and does not mutate its input', () => {
    const before = JSON.stringify(GEO_FIXTURE);
    expect(summarize(GEO_FIXTURE).mismatchCount).toBe(GEO_FIXTURE.mismatches.length);
    expect(JSON.stringify(GEO_FIXTURE)).toBe(before);
  });

  it('reports NO_DATA, not zero, for an empty evidence set', () => {
    const empty = { ...GEO_FIXTURE, jurisdictions: [], corridors: [], mismatches: [] };
    expect(summarize(empty).corridorVolumeUsd).toBeNull();
    expect(summarize(empty).topCorridors).toEqual([]);
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
  it('builds one layer per visible lens with stable ids', () => {
    const ids = buildLayers(GEO_FIXTURE, REFERENCE, ALL, null).map((l) => l.id);
    expect(ids).toEqual(['geo-risk', 'geo-offshore', 'geo-corridors', 'geo-mismatches']);
  });

  it('omits hidden lenses and returns nothing when none is visible', () => {
    expect(buildLayers(GEO_FIXTURE, REFERENCE, new Set<LayerId>(['corridors']), null).map((l) => l.id)).toEqual(['geo-corridors']);
    expect(buildLayers(GEO_FIXTURE, REFERENCE, new Set<LayerId>(), null)).toEqual([]);
  });

  it('draws no reference lens when the reference layer is absent, and keeps the customer-flow lenses', () => {
    const ids = buildLayers(GEO_FIXTURE, null, ALL, null).map((l) => l.id);
    expect(ids).toEqual(['geo-corridors', 'geo-mismatches']);
  });

  it('is deterministic and does not mutate its inputs', () => {
    const before = JSON.stringify([GEO_FIXTURE, REFERENCE]);
    const a = buildLayers(GEO_FIXTURE, REFERENCE, ALL, null).map((l) => l.id);
    const b = buildLayers(GEO_FIXTURE, REFERENCE, ALL, null).map((l) => l.id);
    expect(a).toEqual(b);
    expect(JSON.stringify([GEO_FIXTURE, REFERENCE])).toBe(before);
  });

  it('feeds each layer exactly the evidence rows (no invented marks)', () => {
    const layers = buildLayers(GEO_FIXTURE, REFERENCE, ALL, null);
    const rows = (id: string) => (layers.find((l) => l.id === id)!.props.data as unknown[]).length;
    expect(rows('geo-risk')).toBe(REFERENCE.countries.length);
    expect(rows('geo-offshore')).toBe(
      REFERENCE.countries.filter((c) => (c.entities_incorporated ?? 0) >= MIN_OFFSHORE_ENTITIES).length,
    );
    expect(rows('geo-corridors')).toBe(GEO_FIXTURE.corridors.length);
    expect(rows('geo-mismatches')).toBe(GEO_FIXTURE.mismatches.length);
  });
});
