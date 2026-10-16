import { describe, it, expect } from 'vitest';
import { resolveProofLedgerHash } from '@/components/cockpit/common/topological-graph';

describe('TopologicalGraph proof label resolution (honesty rule)', () => {
  it('omits proof label when no ledger hash or checkpoint exists', () => {
    const state = {
      canvasPayload: null,
      activeDrProofs: [],
    };
    expect(resolveProofLedgerHash(state)).toBeNull();
  });

  it('resolves real ledger hash from canvasPayload when present', () => {
    const state = {
      canvasPayload: { ledgerHash: 'sha256-actual-ledger-abc123' },
      activeDrProofs: [],
    };
    expect(resolveProofLedgerHash(state)).toBe('sha256-actual-ledger-abc123');
  });

  it('resolves real checkpoint hash from activeDrProofs when present', () => {
    const state = {
      canvasPayload: null,
      activeDrProofs: [
        { backupCheckpointHash: '8f4c2e1a9b7d3f6e5a0c8b2d1e4f7a9c3b5d7e1a9b2c4e6f8a0b2d4e6f8a0b2c' },
      ],
    };
    expect(resolveProofLedgerHash(state)).toBe('8f4c2e1a9b7d3f6e5a0c8b2d1e4f7a9c3b5d7e1a9b2c4e6f8a0b2d4e6f8a0b2c');
  });
});
