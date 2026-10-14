'use client';

/**
 * System status: the one place for platform-level health that is not tied to a canvas section.
 * Pipeline connection, resilience (outage / replay) controls, constitutional red-line gates
 * and flywheel calibration. Everything is read from cockpit state; where the backend has not
 * supplied data the dialog says so instead of inventing a value.
 */

import * as React from 'react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { useCockpit } from '../state/cockpit-context';
import { getPipelineStatus } from '../state/pipeline-status';
import { Chip } from '../ui/chip';

const SECTION = 'p-4 border-b border-slate-200 space-y-2.5';
const SECTION_TITLE = 'flex items-center gap-2 text-xs font-bold font-mono uppercase text-slate-900';

export function SystemStatusDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { state, toggleSimulatedOutage } = useCockpit();
  const pipeline = getPipelineStatus(state);
  const gates = state.activeRedLineGates;
  const passing = gates.filter((g) => g.status === 'PASS').length;
  const fw = state.activeFlywheelStatus;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        size="sm"
        className="rounded-none border border-slate-300 bg-white shadow-2xl p-0 overflow-hidden flex flex-col max-h-[85vh]"
      >
        <div className="px-4 h-11 shrink-0 flex items-center justify-between bg-cockpit-rail text-white">
          <DialogTitle className="text-sm font-bold font-mono tracking-wide uppercase text-white">
            System status
          </DialogTitle>
          <button
            type="button"
            aria-label="Close system status"
            onClick={() => onOpenChange(false)}
            className="size-7 flex items-center justify-center text-slate-300 hover:text-white hover:bg-white/10 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-chrome-accent"
          >
            <span className="material-symbols-sharp text-base">close</span>
          </button>
        </div>

        <div className="overflow-y-auto">
          <section aria-label="Pipeline" className={SECTION}>
            <h3 className={SECTION_TITLE}>
              <span className="material-symbols-sharp text-base text-cx-accent">sync_alt</span>
              Pipeline
            </h3>
            <dl className="grid grid-cols-3 gap-2 text-xs font-mono">
              <div className="p-2 bg-slate-50 border border-slate-200">
                <dt className="text-label text-slate-500">Connection</dt>
                <dd data-testid="status-pipeline" className="font-bold text-slate-900">{pipeline.label}</dd>
              </div>
              <div className="p-2 bg-slate-50 border border-slate-200">
                <dt className="text-label text-slate-500">Round trip</dt>
                <dd className="font-bold text-slate-900 tabular-nums">
                  {pipeline.label === 'Replay' ? '—' : `${state.systemLatencyMs}ms`}
                </dd>
              </div>
              <div className="p-2 bg-slate-50 border border-slate-200">
                <dt className="text-label text-slate-500">Data as of</dt>
                <dd className="font-bold text-slate-900 tabular-nums">
                  {state.asOfTimestamp ? `${state.asOfTimestamp.slice(0, 16).replace('T', ' ')}Z` : '—'}
                </dd>
              </div>
            </dl>
          </section>

          <section aria-label="Resilience" className={SECTION}>
            <h3 className={SECTION_TITLE}>
              <span className="material-symbols-sharp text-base text-amber-600">electrical_services</span>
              Resilience
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed font-sans">
              Injects a simulated upstream partition to verify deterministic offline fallback and cryptographic cache
              replay.
            </p>
            <button
              type="button"
              onClick={() => toggleSimulatedOutage()}
              className={`px-3 py-1.5 text-xs font-mono font-medium border transition-colors flex items-center gap-1.5 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-cx-accent ${
                state.isSimulatedOutage
                  ? 'bg-amber-500 border-amber-600 text-slate-950 font-bold'
                  : 'bg-slate-50 hover:bg-slate-100 border-slate-300 text-slate-800'
              }`}
            >
              <span className="material-symbols-sharp text-sm">{state.isSimulatedOutage ? 'bolt' : 'electrical_services'}</span>
              <span>{state.isSimulatedOutage ? 'Restore Live Pipeline Stream' : 'Simulate Outage & Partition Fallback'}</span>
            </button>
          </section>

          <section aria-label="Red-line gates" className={SECTION}>
            <h3 className={`${SECTION_TITLE} justify-between`}>
              <span className="flex items-center gap-2">
                <span className="material-symbols-sharp text-base text-green-600">verified</span>
                Red-line gates
              </span>
              {gates.length > 0 && (
                <span className="text-label px-1.5 py-0.5 border bg-slate-50 border-slate-300 text-slate-700">
                  {`${passing}/${gates.length} PASS`}
                </span>
              )}
            </h3>
            {gates.length === 0 ? (
              <p className="text-xs text-slate-500 font-sans">No gate evaluation received from the backend.</p>
            ) : (
              <>
                <p className="text-label text-slate-500 font-mono">
                  [ILLUSTRATIVE] contract fixture: live gate evaluation is not wired to this panel yet.
                </p>
                <ul className="grid grid-cols-1 gap-1.5">
                  {gates.map((g) => (
                    <li key={g.gateId} className="p-2 bg-slate-50 border border-slate-200 flex items-center justify-between gap-2 text-xs">
                      <span className="min-w-0">
                        <span className="font-mono font-bold text-slate-900 mr-1.5">{g.gateId}</span>
                        <span className="text-slate-700">{g.name}</span>
                      </span>
                      <Chip tone={g.status === 'PASS' ? 'ok' : 'bad'} className="shrink-0">{g.status}</Chip>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>

          <section aria-label="Flywheel calibration" className={`${SECTION} border-b-0`}>
            <h3 className={SECTION_TITLE}>
              <span className="material-symbols-sharp text-base text-blue-600">psychology_alt</span>
              Flywheel calibration
            </h3>
            <dl className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2 bg-slate-50 border border-slate-200">
                <dt className="text-label text-slate-500">Brier score</dt>
                <dd className="font-bold text-slate-900 tabular-nums">{fw?.shadowModelBrierScore?.toFixed(3) ?? '—'}</dd>
              </div>
              <div className="p-2 bg-slate-50 border border-slate-200">
                <dt className="text-label text-slate-500">Feedback events</dt>
                <dd className="font-bold text-slate-900 tabular-nums">{fw?.totalFeedbackEvents ?? '—'}</dd>
              </div>
              <div className="p-2 bg-slate-50 border border-slate-200">
                <dt className="text-label text-slate-500">Uncalibrated</dt>
                <dd className="font-bold text-amber-700 tabular-nums">{fw?.uncalibratedDiscrepancies ?? '—'}</dd>
              </div>
              <div className="p-2 bg-slate-50 border border-slate-200">
                <dt className="text-label text-slate-500">Calibration drift</dt>
                <dd className={`font-bold ${!fw ? 'text-slate-400' : fw.calibrationDriftDetected ? 'text-red-700' : 'text-green-700'}`}>
                  {!fw ? '—' : fw.calibrationDriftDetected ? 'DRIFT DETECTED' : 'NOMINAL'}
                </dd>
              </div>
            </dl>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
