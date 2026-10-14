'use client';

import * as React from 'react';
import { authFetch } from '@/lib/auth/token';
import type { ComplianceLedger } from '../state/cockpit-types';

export type LedgerState =
  | { status: 'loading' }
  | { status: 'error'; httpStatus: number }
  | { status: 'ready'; ledger: ComplianceLedger };

export interface AuditWalk {
  status: 'VALID' | 'TAMPERED';
  totalRecords: number;
  checkpointsVerified: number;
  tamperedSeq: number | null;
  verifiedAt: string;
}

/** The decision ledger from the backend; `reload` re-reads it after the shelf or a verification changed it. */
export function useComplianceLedger(): { state: LedgerState; reload: () => void } {
  const [state, setState] = React.useState<LedgerState>({ status: 'loading' });
  const [tick, setTick] = React.useState(0);

  React.useEffect(() => {
    let live = true;
    authFetch('/api/cockpit/compliance/ledger', { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        if (!live) return;
        if (!res.ok) return setState({ status: 'error', httpStatus: res.status });
        setState({ status: 'ready', ledger: (await res.json()) as ComplianceLedger });
      })
      .catch(() => live && setState({ status: 'error', httpStatus: 0 }));
    return () => {
      live = false;
    };
  }, [tick]);

  return { state, reload: React.useCallback(() => setTick((t) => t + 1), []) };
}

/** Walks the ledger on the backend: sequence, hash chain and signed checkpoints. Null when the walk failed. */
export async function walkLedger(): Promise<AuditWalk | null> {
  try {
    const res = await authFetch('/api/cockpit/audit/verify', { headers: { Accept: 'application/json' } });
    if (!res.ok) return null;
    const r = await res.json();
    return {
      status: r.status === 'VALID' ? 'VALID' : 'TAMPERED',
      totalRecords: Number(r.total_records ?? 0),
      checkpointsVerified: Number(r.worm_checkpoints_verified ?? 0),
      tamperedSeq: typeof r.tampered_sequence_id === 'number' ? r.tampered_sequence_id : null,
      verifiedAt: String(r.verified_at ?? ''),
    };
  } catch {
    return null;
  }
}
