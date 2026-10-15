import { describe, it, expect } from 'vitest';
import { formatGeoUrl, parseGeoUrl } from '@/components/cockpit/geo/geo-url';

describe('geo URL state', () => {
  it('round-trips a view and a pick, keeping other parameters', () => {
    const search = formatGeoUrl('?foo=1', 'logins', { kind: 'mismatch', id: 'ID>NG' });
    expect(search).toContain('foo=1');
    expect(parseGeoUrl(search)).toEqual({ view: 'logins', selection: { kind: 'mismatch', id: 'ID>NG' }, basis: null });
    expect(parseGeoUrl(formatGeoUrl(search, 'corridors', null))).toEqual({ view: 'corridors', selection: null, basis: null });
  });

  it('reads every kind of pick the map can make', () => {
    for (const sel of ['country:IR', 'corridor:MM>ID', 'gateway:GW-NG-X00', 'account:CR84920']) {
      expect(parseGeoUrl(`?sel=${encodeURIComponent(sel)}`).selection?.id).toBe(sel.slice(sel.indexOf(':') + 1));
    }
  });

  it('ignores anything it does not recognise instead of guessing', () => {
    expect(parseGeoUrl('?view=nope&sel=planet:Mars')).toEqual({ view: null, selection: null, basis: null });
    expect(parseGeoUrl('?sel=account:<script>')).toEqual({ view: null, selection: null, basis: null });
    expect(parseGeoUrl('?sel=account')).toEqual({ view: null, selection: null, basis: null });
    expect(parseGeoUrl('')).toEqual({ view: null, selection: null, basis: null });
  });
});
