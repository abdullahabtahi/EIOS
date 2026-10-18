import { describe, expect, it } from 'vitest';
import { moveLabel } from '@/components/cockpit/geo/geo-moves';

const NAMES: Record<string, string> = { ID: 'Indonesia', MM: 'Myanmar' };
const name = (code: string) => NAMES[code] ?? code;

describe('the label of a map move', () => {
  it('names the countries of a corridor instead of showing their codes', () => {
    expect(moveLabel({ kind: 'corridor', id: 'ID>MM' }, name)).toBe('corridor Indonesia → Myanmar');
  });
  it('names a country, and leaves an account id as it is', () => {
    expect(moveLabel({ kind: 'country', id: 'MM' }, name)).toBe('country Myanmar');
    expect(moveLabel({ kind: 'account', id: 'CR11568' }, name)).toBe('account CR11568');
  });
  it('falls back to the codes when no names are loaded', () => {
    expect(moveLabel({ kind: 'corridor', id: 'ID>MM' })).toBe('corridor ID → MM');
  });
});
