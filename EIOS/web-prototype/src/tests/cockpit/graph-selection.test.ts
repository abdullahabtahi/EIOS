import { describe, expect, it } from 'vitest';
import { nodeOpensCase } from '@/components/cockpit/common/graph-selection';

const node = (type: string) => ({ details: { type } });

describe('Selecting a graph node opens a case only when it is an account', () => {
  it.each(['shared device fingerprint', 'device fingerprint', 'payment agent', 'collapsed cluster hub', 'ip address', 'partner account'])(
    'does not request a case for a %s when the data is engine-computed',
    (type) => expect(nodeOpensCase(node(type), 'engine')).toBe(false),
  );

  it('opens a case for a client account', () => {
    expect(nodeOpensCase(node('client account'), 'engine')).toBe(true);
  });

  it('keeps the sample workstation behaviour for fixture data', () => {
    expect(nodeOpensCase(node('device fingerprint'), 'fixture')).toBe(true);
    expect(nodeOpensCase({ details: {} }, 'live')).toBe(true);
  });

  it('treats a node with no type as not an account under engine data', () => {
    expect(nodeOpensCase({ details: {} }, 'engine')).toBe(false);
  });
});
