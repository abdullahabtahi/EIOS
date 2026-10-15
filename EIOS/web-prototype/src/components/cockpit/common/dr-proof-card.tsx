'use client';

/**
 * Disaster Recovery & Hardening Proof Card (Feature 015)
 * Enforces Constitution Principle VIII (Disaster Recovery & Deterministic Failover).
 * Displays automated Cloud KMS keyring rotation status, immutable backup checkpoint hash,
 * and warm-start cache health.
 * Strict Institutional Light Mode.
 */

import { DisasterRecoveryProof } from '../state/cockpit-types';
import { formatUtcTimestamp } from '@/lib/utils';

interface DrProofCardProps {
  proof?: DisasterRecoveryProof;
}

/** The recovery proof the backend measured. With none, the card says no drill has been run: it shows no stand-in. */
export function DrProofCard({ proof }: DrProofCardProps) {
  if (!proof) {
    return (
      <div className="bg-white border border-slate-200 p-4 shadow-sm font-mono text-xs">
        <h4 className="text-title font-sans font-semibold tracking-normal text-slate-900">Disaster Recovery Proof</h4>
        <p className="text-label text-slate-500 font-sans mt-1">No recovery drill has been run on this plane.</p>
      </div>
    );
  }
  const passed = proof.verificationStatus === 'PASS';
  const drilled = proof.rowsRestored !== undefined && proof.rowsExported !== undefined;
  return (
    <div className="bg-white border border-slate-200 p-4 shadow-sm space-y-3 font-mono text-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-blue-700">shield_lock</span>
          <div>
            <h4 className="text-title font-sans font-semibold tracking-normal text-slate-900">Disaster Recovery Proof</h4>
            <span className="text-label text-slate-500 font-sans">
              Runbook: {proof.runbookId}: {proof.runbookName}
            </span>
          </div>
        </div>
        <span
          className={`px-2 py-0.5 border text-label font-bold ${
            passed ? 'bg-green-50 text-green-800 border-green-300' : 'bg-red-50 text-red-800 border-red-300'
          }`}
        >
          STATUS: {proof.verificationStatus}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
        <div className="p-2.5 bg-slate-50 border border-slate-200">
          <span className="text-label text-slate-500 block uppercase">Rows restored</span>
          <span className="font-bold text-slate-800 text-label block mt-0.5 tabular-nums">
            {drilled ? `${proof.rowsRestored!.toLocaleString('en-US')} of ${proof.rowsExported!.toLocaleString('en-US')}` : '—'}
          </span>
          <span className="text-label text-slate-400 block mt-0.5">
            {proof.restoreMs !== undefined ? `Rehydration took ${proof.restoreMs.toFixed(0)} ms` : 'Not measured'}
          </span>
        </div>
        <div className="p-2.5 bg-slate-50 border border-slate-200">
          <span className="text-label text-slate-500 block uppercase">Cloud KMS keyring rotation</span>
          <span className="font-bold text-slate-800 text-label block mt-0.5">{proof.kmsKeyringRotationStatus.replace('_', ' ')}</span>
          <span className="text-label text-slate-400 block mt-0.5">A restore drill does not test key rotation</span>
        </div>
        <div className="p-2.5 bg-slate-50 border border-slate-200">
          <span className="text-label text-slate-500 block uppercase">Drill run at</span>
          <span className="font-bold text-slate-800 text-label block mt-0.5">{formatUtcTimestamp(proof.lastExecutedTimestamp)}</span>
          <span className="text-label text-slate-400 block mt-0.5">Warm-start cache: {proof.warmStartCacheState}</span>
        </div>
      </div>

      <div className="p-2 bg-slate-100 border border-slate-200 flex items-center justify-between text-label gap-2">
        <span className="text-slate-500 shrink-0">Backup checkpoint hash (SHA-256):</span>
        <span className="font-mono text-slate-800 truncate max-w-md">{proof.backupCheckpointHash}</span>
      </div>
    </div>
  );
}
