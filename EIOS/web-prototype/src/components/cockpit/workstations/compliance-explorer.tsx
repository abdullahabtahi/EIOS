'use client';

/**
 * Compliance & Audit Explorer (spec 032): the decision ledger the action shelf writes to, every intent's
 * four-eyes sign-offs, the signed checkpoints, and an audit walk the auditor can run. Nothing on this screen is
 * filled in: an empty ledger says it is empty and a failed load says so.
 */

import * as React from 'react';
import { DrProofCard } from '../common/dr-proof-card';
import { formatUtcTimestamp } from '@/lib/utils';
import type { ComplianceLedger, IntentSignOffs, LedgerRow } from '../state/cockpit-types';
import { type AuditWalk, useComplianceLedger, walkLedger } from './use-compliance-ledger';

const plural = (n: number, word: string) => `${n.toLocaleString()} ${word}${n === 1 ? '' : 's'}`;
const sentence = (code: string) => code.replace(/_/g, ' ').toLowerCase();

function LedgerEntry({ row }: { row: LedgerRow }) {
  return (
    <div className="p-3.5 bg-cx-sub border border-cx-line space-y-2 rounded-none">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="px-1.5 py-0.2 bg-cx-info-bg text-cx-accent border border-cx-info-line font-bold text-label">
            SEQ #{row.ledgerSeq}
          </span>
          <span className="font-bold text-cx-ink">{sentence(row.eventType)}</span>
          <span className="text-cx-muted">by {row.actorId}</span>
        </div>
        <div className="flex items-center gap-2 text-label">
          <span className="text-cx-faint">{formatUtcTimestamp(row.timestamp)}</span>
          <span className="px-1.5 py-0.2 bg-cx-sub text-cx-muted border border-cx-line font-bold">
            {row.anchored ? 'Checkpointed' : 'Not yet checkpointed'}
          </span>
        </div>
      </div>
      <div className="p-2 bg-white border border-cx-line text-label space-y-1">
        <div className="truncate">
          <span className="text-cx-faint">Intent: </span>
          <span className="text-cx-ink">{row.entityId}</span>
        </div>
        <div className="truncate">
          <span className="text-cx-faint">Hash: </span>
          <span className="text-cx-ink font-semibold">{row.recordHash}</span>
        </div>
        <div className="truncate">
          <span className="text-cx-faint">Previous: </span>
          <span className="text-cx-muted">{row.previousHash}</span>
        </div>
      </div>
    </div>
  );
}

function SignOffRow({ intent }: { intent: IntentSignOffs }) {
  const pending = intent.requiresDualApproval && !intent.second;
  return (
    <li className="p-3 bg-cx-sub border border-cx-line space-y-1">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-bold text-cx-ink">
          {intent.actionType} <span className="text-cx-muted font-normal">[{intent.targetEntityId || 'no target'}]</span>
        </span>
        <span className="text-label font-bold text-cx-muted">{sentence(intent.status)}</span>
      </div>
      <div className="text-label text-cx-muted">
        First: {intent.first ? `${intent.first.role} (${intent.first.officerId})` : 'awaiting approval'}
        {' · '}
        Second:{' '}
        {intent.second
          ? `${intent.second.role} (${intent.second.officerId})`
          : pending
            ? 'awaiting second approver'
            : 'not required'}
      </div>
    </li>
  );
}

function Verification({ ledger, walk }: { ledger: ComplianceLedger; walk: AuditWalk | null }) {
  const v = ledger.verification;
  const checkpoint = ledger.checkpoints.at(-1);
  const status = walk ? walk.status === 'VALID' : v.unbroken;
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono">
      <div className="p-2.5 bg-cx-sub border border-cx-line">
        <span className="text-label text-cx-muted block">Entries walked</span>
        <div className="text-base font-bold text-cx-ink mt-0.5">{plural(walk?.totalRecords ?? v.entriesVerified, 'entry')}</div>
        <span className="text-label text-cx-muted block mt-0.5">
          {status ? 'Sequence and hash chain intact' : `Break at entry ${walk?.tamperedSeq ?? '?'}`}
        </span>
      </div>
      <div className="p-2.5 bg-cx-sub border border-cx-line">
        <span className="text-label text-cx-muted block">Signed checkpoints</span>
        <div className="text-base font-bold text-cx-ink mt-0.5">{plural(ledger.checkpoints.length, 'checkpoint')}</div>
        <span className="text-label text-cx-muted block mt-0.5">
          {checkpoint ? `Head at entry ${checkpoint.chainHeadSeq}, retained to ${checkpoint.retentionExpiration.slice(0, 10)}` : 'No checkpoint taken yet'}
        </span>
      </div>
      <div className="p-2.5 bg-cx-sub border border-cx-line">
        <span className="text-label text-cx-muted block">Four-eyes sign-offs</span>
        <div className="text-base font-bold text-cx-ink mt-0.5">
          {plural(ledger.approvals.filter((a) => a.second).length, 'dual approval')}
        </div>
        <span className="text-label text-cx-muted block mt-0.5">{plural(ledger.approvals.length, 'intent')} on the ledger</span>
      </div>
    </div>
  );
}

function LedgerBody({ ledger }: { ledger: ComplianceLedger }) {
  if (ledger.entries.length === 0) {
    return <p className="text-cx-muted font-sans">The ledger is empty: no action has been staged yet.</p>;
  }
  return (
    <div className="space-y-3">
      {ledger.entries.map((row) => (
        <LedgerEntry key={row.ledgerSeq} row={row} />
      ))}
    </div>
  );
}

export function ComplianceExplorerView() {
  const { state, reload } = useComplianceLedger();
  const [walk, setWalk] = React.useState<AuditWalk | null>(null);
  const [walking, setWalking] = React.useState(false);
  const [walkFailed, setWalkFailed] = React.useState(false);

  const verify = async () => {
    setWalking(true);
    const result = await walkLedger();
    setWalk(result);
    setWalkFailed(result === null);
    setWalking(false);
    reload();
  };

  if (state.status === 'loading') {
    return <p className="text-xs text-cx-muted p-4">Loading the decision ledger…</p>;
  }
  if (state.status === 'error') {
    return (
      <p role="alert" className="text-xs text-cx-bad p-4">
        The decision ledger could not be loaded{state.httpStatus ? ` (HTTP ${state.httpStatus})` : ''}.
      </p>
    );
  }
  const { ledger } = state;

  return (
    <div className="space-y-6 text-cx-ink pb-10">
      <div role="tabpanel" id="panel-ledger" aria-label="Decision ledger entries" className="block">
        <section aria-label="Sequential Ledger Entries" className="bg-white border border-cx-line p-4 shadow-xs space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-cx-line-soft pb-2">
            <h3 className="text-title font-sans font-semibold tracking-normal text-cx-ink">Decision ledger</h3>
            <span className="text-label text-cx-faint">{plural(ledger.entries.length, 'entry')}, newest first</span>
          </div>
          <LedgerBody ledger={ledger} />
        </section>
      </div>

      <div role="tabpanel" id="panel-signoffs" aria-label="Four-eyes sign-offs" className="block">
        <section className="bg-white border border-cx-line p-4 shadow-xs space-y-3 font-mono text-xs">
          <h3 className="text-title font-sans font-semibold tracking-normal text-cx-ink border-b border-cx-line-soft pb-2">
            Four-eyes sign-offs
          </h3>
          {ledger.approvals.length === 0 ? (
            <p className="text-cx-muted font-sans">No intent has been staged yet.</p>
          ) : (
            <ul className="space-y-2">
              {ledger.approvals.map((intent) => (
                <SignOffRow key={intent.intentId} intent={intent} />
              ))}
            </ul>
          )}
        </section>
      </div>

      <div role="tabpanel" id="panel-verifier" aria-label="Hash Chain Verification" className="block">
        <section aria-label="Hash Chain Verification Bar" className="bg-white border border-cx-line p-4 shadow-sm space-y-3 font-mono text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cx-line-soft pb-3">
            <h3 className="text-title font-sans font-semibold tracking-normal text-cx-ink">Ledger chain continuity</h3>
            <div className="flex items-center gap-2">
              {walk && (
                <span className="text-label text-cx-muted">Walked {formatUtcTimestamp(walk.verifiedAt)}</span>
              )}
              {walkFailed && (
                <span role="alert" className="text-label text-cx-bad">The audit walk failed</span>
              )}
              <button
                type="button"
                disabled={walking}
                onClick={verify}
                className="px-3 py-1 bg-cx-ink hover:bg-cx-ink-hover text-white text-xs font-semibold rounded-none cursor-pointer flex items-center gap-1 transition-colors"
              >
                <span className={`material-symbols-sharp text-sm ${walking ? 'animate-spin' : ''}`}>sync</span>
                Verify Chain Continuity
              </button>
            </div>
          </div>
          <Verification ledger={ledger} walk={walk} />
        </section>
      </div>

      <div role="tabpanel" id="panel-dr" aria-label="Disaster Recovery Proofs" className="block">
        <DrProofCard />
      </div>
    </div>
  );
}
