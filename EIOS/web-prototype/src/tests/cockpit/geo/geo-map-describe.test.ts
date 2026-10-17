import { describe, it, expect } from 'vitest';
import { describeMap } from '@/components/cockpit/geo/geo-map-describe';
import { viewOf } from '@/components/cockpit/geo/geo-views';
import { FLOWS } from './flows-fixture';

describe('the map described in words', () => {
  it('names the view and what is drawn, from the same counts as the legend', () => {
    const text = describeMap('corridors', viewOf('corridors').layers, FLOWS, null);
    expect(text).toContain('Corridors map');
    expect(text).toContain('Showing 3 of 3 corridors');
  });

  it('says nothing is picked, or what is, in the words of the list', () => {
    expect(describeMap('corridors', viewOf('corridors').layers, FLOWS, null)).toContain('Nothing is picked');
    expect(describeMap('corridors', viewOf('corridors').layers, FLOWS, { kind: 'corridor', id: 'NO>IR' })).toContain('Picked: corridor NO to IR');
    expect(describeMap('jurisdictions', viewOf('jurisdictions').layers, FLOWS, { kind: 'country', id: 'KE' })).toContain('Picked: country KE');
  });

  it('replaces every arrow in a route id, not only the first', () => {
    expect(describeMap('corridors', viewOf('corridors').layers, FLOWS, { kind: 'corridor', id: 'NO>IR>KE' })).toContain('corridor NO to IR to KE');
  });

  it('describes a view with no flows yet without inventing counts', () => {
    const text = describeMap('jurisdictions', viewOf('jurisdictions').layers, null, null);
    expect(text).toContain('Jurisdictions map');
    expect(text).not.toMatch(/\d+ of \d+/);
  });

  it('says how the focused map pans and zooms', () => {
    expect(describeMap('corridors', viewOf('corridors').layers, FLOWS, null)).toMatch(/arrow keys pan.*plus and minus zoom/);
  });

  it('points to the list and the assistant as the keyboard route', () => {
    expect(describeMap('logins', viewOf('logins').layers, FLOWS, null)).toMatch(/list/i);
    expect(describeMap('logins', viewOf('logins').layers, FLOWS, null)).toContain('slash');
  });
});
