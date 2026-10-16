import { describe, it, expect } from 'vitest';
import { geoSuggestions, mapContextOf, moveLabel, stateAfterMove, viewForKind } from '@/components/cockpit/geo/geo-moves';
import { normalizeViewCommands } from '@/lib/server/normalize';
import { buildLayers } from '@/components/cockpit/geo/geo-layers';
import { REFERENCE } from './reference-fixture';

describe('map moves', () => {
  it('opens the view that shows each kind of object', () => {
    expect(viewForKind('country')).toBe('jurisdictions');
    expect(viewForKind('corridor')).toBe('corridors');
    expect(['gateway', 'mismatch', 'account'].map((k) => viewForKind(k as 'gateway'))).toEqual(['logins', 'logins', 'logins']);
  });

  it('selects the object a move names and keeps the colouring basis', () => {
    const before = { view: 'jurisdictions' as const, selected: null, basis: 'eu' as const };
    expect(stateAfterMove(before, { kind: 'gateway', id: 'GW-NG-X00' })).toEqual({
      view: 'logins',
      selected: { kind: 'gateway', id: 'GW-NG-X00' },
      basis: 'eu',
    });
  });

  it('sends the selection, and the basis only on the Jurisdictions view', () => {
    expect(mapContextOf({ view: 'corridors', selected: null, basis: 'fatf' })).toEqual({ view: 'corridors' });
    expect(mapContextOf({ view: 'jurisdictions', selected: { kind: 'country', id: 'NG' }, basis: 'basel' })).toEqual({
      view: 'jurisdictions',
      selection: { kind: 'country', id: 'NG' },
      basis: 'basel',
    });
  });

  it('labels a move in words and offers questions about what is selected', () => {
    expect(moveLabel({ kind: 'corridor', id: 'ID>MM' })).toBe('corridor ID → MM');
    expect(geoSuggestions({ kind: 'gateway', id: 'GW-NG-X00' })[0]).toMatch(/exit/);
    expect(geoSuggestions(null)[0]).toBe('Where should I look first?');
  });
});

describe('view commands from the backend', () => {
  it('keeps a move in the map vocabulary and drops anything else, never repairing it', () => {
    expect(
      normalizeViewCommands([
        { kind: 'gateway', id: 'GW-NG-X00' },
        { kind: 'planet', id: 'X' },
        { kind: 'country', id: 'NG; drop' },
        { kind: 'corridor', id: 'ID>MM' },
        'gateway:GW-NG-X00',
        null,
      ]),
    ).toEqual([
      { kind: 'gateway', id: 'GW-NG-X00' },
      { kind: 'corridor', id: 'ID>MM' },
    ]);
    expect(normalizeViewCommands(undefined)).toEqual([]);
  });
});

describe('list-change outlines', () => {
  it('outlines the countries a change names, and nothing without one', () => {
    const ids = (marks: Parameters<typeof buildLayers>[7]) =>
      buildLayers(null, REFERENCE, new Set(), null, {}, [], 'fatf', marks).map((l) => l.id);
    expect(ids({ added: new Set(['KE']), removed: new Set(['NO']) })).toContain('geo-list-change');
    expect(ids(null)).not.toContain('geo-list-change');
    expect(ids({ added: new Set(['ZZ']), removed: new Set() })).not.toContain('geo-list-change');
  });
});
