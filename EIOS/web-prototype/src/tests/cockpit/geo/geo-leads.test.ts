import { describe, it, expect } from 'vitest';
import { leadsFor } from '@/components/cockpit/geo/geo-leads';
import { cameraFor, COUNTRY_ZOOM, MIN_SPAN_DEG } from '@/components/cockpit/geo/geo-camera';
import { shownCorridors } from '@/components/cockpit/geo/geo-rank';
import { drawnCounts } from '@/components/cockpit/geo/geo-legend';
import { VIEWS, DEFAULT_VIEW, viewOf } from '@/components/cockpit/geo/geo-views';
import { focusFor, focusOf, REGION_ZOOM } from '@/components/cockpit/geo/geo-focus';
import type { LayerId } from '@/components/cockpit/geo/geo-types';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';

describe('leadsFor', () => {
  it('lists corridors in the order the map draws them, elevated first, with country names', () => {
    const leads = leadsFor('corridors', FLOWS, REFERENCE)!;
    expect(leads.map((l) => l.title)).toEqual(['Norway → Iran', 'Kenya → The Bahamas', 'Panama → Norway']);
    expect(leads.map((l) => l.tier)).toEqual(['high', 'medium', null]);
    expect(leads[0].detail).toBe('$900K · 4 accounts');
    expect(leads.slice(0, shownCorridors(FLOWS).length).map((l) => l.selection.id)).toEqual(
      shownCorridors(FLOWS).map((c) => `${c.origin}>${c.destination}`),
    );
  });

  it('does not flag a low or unrated corridor', () => {
    const unrated = { ...FLOWS, corridors: FLOWS.corridors.map((c) => ({ ...c, tier: null })) };
    expect(leadsFor('corridors', unrated, REFERENCE)!.every((l) => l.tier === null)).toBe(true);
  });

  it('lists flagged country pairs, the most accounts first, and singularises one account', () => {
    const leads = leadsFor('logins', FLOWS, REFERENCE)!;
    expect(leads.map((l) => l.title)).toEqual(['Norway → Kenya', 'Panama → The Bahamas']);
    expect(leads[0].detail).toBe('23 accounts · 80 of 90 logins abroad');
    expect(leads[1].detail).toMatch(/^2 accounts/);
    expect(leadsFor('logins', { ...FLOWS, mismatch_pairs: [{ ...FLOWS.mismatch_pairs[1], accounts: 1 }] }, REFERENCE)![0].detail).toMatch(/^1 account ·/);
  });

  it('groups jurisdictions: call-for-action countries, then the largest offshore centres', () => {
    const leads = leadsFor('jurisdictions', null, REFERENCE)!;
    expect(leads.filter((l) => l.group === 'On the FATF call-for-action list').map((l) => l.title)).toEqual(['Iran']);
    expect(leads.filter((l) => l.group === 'Largest offshore centres').map((l) => l.title)).toEqual(['The Bahamas', 'Panama', 'Kenya']);
  });

  it('is null (no data), not empty, when the data a view needs is absent; empty only when measured empty', () => {
    expect(leadsFor('corridors', null, REFERENCE)).toBeNull();
    expect(leadsFor('logins', null, REFERENCE)).toBeNull();
    expect(leadsFor('jurisdictions', FLOWS, null)).toBeNull();
    expect(leadsFor('corridors', { ...FLOWS, corridors: [] }, REFERENCE)).toEqual([]);
  });

  it('falls back to the country code when the reference layer cannot name it', () => {
    expect(leadsFor('corridors', FLOWS, null)![0].title).toBe('NO → IR');
  });
});

describe('cameraFor', () => {
  it('frames both ends of a corridor, never tighter than the minimum span', () => {
    const t = cameraFor({ kind: 'corridor', id: 'NO>IR' }, FLOWS, REFERENCE)!;
    expect(t.kind).toBe('bounds');
    if (t.kind !== 'bounds') return;
    expect(t.west).toBeLessThanOrEqual(9);
    expect(t.east).toBeGreaterThanOrEqual(53.7);
    expect(t.north - t.south).toBeGreaterThanOrEqual(MIN_SPAN_DEG);
  });

  it('centres on a country', () => {
    expect(cameraFor({ kind: 'country', id: 'KE' }, FLOWS, REFERENCE)).toEqual({ kind: 'point', center: { lat: 0.2, lng: 37.9 }, zoom: COUNTRY_ZOOM });
  });

  it('moves nothing when it cannot place the mark, rather than jumping somewhere invented', () => {
    expect(cameraFor(null, FLOWS, REFERENCE)).toBeNull();
    expect(cameraFor({ kind: 'corridor', id: 'ZZ>IR' }, FLOWS, REFERENCE)).toBeNull();
    expect(cameraFor({ kind: 'corridor', id: 'NO>IR' }, FLOWS, null)).toBeNull();
    expect(cameraFor({ kind: 'country', id: 'ZZ' }, FLOWS, REFERENCE)).toBeNull();
  });
});

describe('views', () => {
  it('opens on the corridors view, and every view names its question and at least one layer', () => {
    expect(DEFAULT_VIEW).toBe('corridors');
    expect(VIEWS.map((v) => v.id)).toEqual(['corridors', 'logins', 'jurisdictions']);
    for (const v of VIEWS) {
      expect(v.question.endsWith('?')).toBe(true);
      expect(v.layers.size).toBeGreaterThan(0);
    }
    expect(viewOf('logins').layers).toEqual(new Set(['mismatches']));
  });

  it('keeps the first screen to what the question needs: no offshore bubbles or login arcs on corridors', () => {
    expect([...viewOf('corridors').layers].sort()).toEqual(['corridors', 'risk']);
  });
});

describe('drawnCounts', () => {
  it('says how much of the data the map draws, from the same ranking, and nothing for hidden layers', () => {
    expect(drawnCounts(FLOWS, new Set<LayerId>(['corridors']))).toEqual(['3 of 3 corridors']);
    expect(drawnCounts(FLOWS, new Set<LayerId>(['risk']))).toEqual([]);
    expect(drawnCounts(null, new Set<LayerId>(['corridors']))).toEqual([]);
  });
});

describe('focusFor', () => {
  it('opens each view on its own framing', () => {
    expect(focusFor('corridors', FLOWS, REFERENCE)).toEqual(focusOf(FLOWS, REFERENCE));
    expect(focusFor('jurisdictions', null, null)?.zoom).toBe(2); // the whole world, and it needs no data to say so
    const logins = focusFor('logins', FLOWS, REFERENCE)!;
    expect(logins.zoom).toBe(REGION_ZOOM);
    // the pairs are Norway-Kenya (23 accounts) and Panama-Bahamas (2): the centre sits near the first
    expect(Math.abs(logins.center.lng - 23)).toBeLessThan(Math.abs(logins.center.lng - -78));
  });

  it('moves nothing when the data a view is framed on is absent', () => {
    expect(focusFor('corridors', null, REFERENCE)).toBeNull();
    expect(focusFor('logins', FLOWS, null)).toBeNull();
    expect(focusFor('logins', { ...FLOWS, mismatch_pairs: [] }, REFERENCE)).toBeNull();
  });
});
