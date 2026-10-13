'use client';

/**
 * Data Platform Operations Board (User Story 5 / Features 012, 015)
 * Displays 6 Data Product SLA freshness monitors (< 30s),
 * DLQ quarantine depth, continuous evaluation error budget burndowns across 10 SLOs,
 * Red-Line test gates (RL-1..RL-7), and Disaster Recovery Runbook proofs.
 * Strict Institutional Light Mode.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { DrProofCard } from '../common/dr-proof-card';
import { buildOperationsView, type OpsStatus, type OpsTone } from '../state/operations-view-model';
import { Chip, type ChipTone } from '../ui/chip';
import { PanelHeader } from '../ui/panel-header';
import { authFetch } from '@/lib/auth/token';

const STATUS_TONE: Record<OpsStatus, ChipTone> = { HEALTHY: 'ok', DEGRADED: 'warn', BREACHED: 'bad' };
const STATUS_BAR: Record<OpsStatus, string> = {
  HEALTHY: 'bg-cx-ok-solid',
  DEGRADED: 'bg-cx-warn-solid',
  BREACHED: 'bg-cx-bad-solid',
};
const SUMMARY_TONE: Record<OpsTone, ChipTone> = { ok: 'ok', warn: 'warn', bad: 'bad' };

export function OperationsBoardView() {
  const { state, toggleSimulatedOutage } = useCockpit();
  const view = React.useMemo(() => buildOperationsView(state.canvasPayload), [state.canvasPayload]);
  const [redrive, setRedrive] = React.useState<Record<string, { ok: boolean; message: string }>>({});

  const redriveRecord = async (id: string) => {
    try {
      const res = await authFetch('/api/v1/ops/dlq/redrive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dlq_id: id }),
      });
      setRedrive((prev) => ({
        ...prev,
        [id]: res.ok
          ? { ok: true, message: `Redrive dispatched for ${id}` }
          : { ok: false, message: `Redrive failed for ${id}: DLQ service responded ${res.status}` },
      }));
    } catch {
      setRedrive((prev) => ({ ...prev, [id]: { ok: false, message: `Redrive failed for ${id}: DLQ service unreachable` } }));
    }
  };

  return (
    <div className="space-y-6 text-slate-900 font-mono text-xs pb-10">
      {/* Surface 1: SLA Freshness Monitors & Telemetry (Anchor: panel-slos) */}
      <div
        role="tabpanel"
        id="panel-slos"
        aria-label="Data Product Freshness SLOs"
        className="block"
      >
        <section aria-label="SLA Freshness Monitors" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3">
          <PanelHeader
            icon="speed"
            title="Data Product SLA Freshness & Error Budget Burndowns"
            actions={
              <>
                {view.source === 'baseline' && <Chip>[ILLUSTRATIVE] baseline</Chip>}
                <Chip tone={SUMMARY_TONE[view.summary.tone]}>{view.summary.label}</Chip>
              </>
            }
          />

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {view.cards.map((card) => (
              <div key={card.id} className="p-3 bg-cx-sub border border-cx-line space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-cx-ink text-label truncate" title={card.name}>{card.name}</span>
                  <Chip tone={STATUS_TONE[card.status]}>{card.status}</Chip>
                </div>

                <div className="flex items-baseline justify-between pt-1">
                  <span className="text-cx-muted text-label shrink-0">{card.primaryLabel}:</span>
                  <span className="font-bold text-cx-ink text-sm tabular-nums">{card.primary}</span>
                </div>

                {(card.details.length > 0 || card.budgetRemainingPct !== null) && (
                  <div className="space-y-1 pt-1 border-t border-cx-line-soft text-label">
                    {card.details.map((d) => (
                      <div key={d.label} className="flex justify-between gap-2 text-cx-muted">
                        <span className="shrink-0">{d.label}:</span>
                        <span className="text-cx-ink font-semibold tabular-nums whitespace-nowrap">{d.value}</span>
                      </div>
                    ))}
                    {card.budgetRemainingPct !== null && (
                      <>
                        {card.primaryLabel !== 'Error budget left' && (
                          <div className="flex justify-between text-cx-muted">
                            <span>Error Budget Remaining:</span>
                            <span className="text-cx-ink font-semibold tabular-nums">{card.budgetRemainingPct}%</span>
                          </div>
                        )}
                        <div className="w-full h-1.5 bg-cx-line-soft">
                          <div
                            className={`h-full ${STATUS_BAR[card.status]}`}
                            style={{ width: `${card.budgetRemainingPct}%` }}
                          />
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Surface 2: Red-Line Test Gates (RL-1 to RL-7) (Anchor: panel-redlines) */}
      <div
        role="tabpanel"
        id="panel-redlines"
        aria-label="Red-Line Test Gates"
        className="block"
      >
        <section aria-label="Red-Line Test Gates" className="bg-white border border-cx-line p-4 shadow-xs space-y-3">
          <PanelHeader
            icon="verified"
            title="Continuous Governance Red-Line Gates (RL-1 to RL-7)"
            actions={<Chip tone={SUMMARY_TONE[view.gateSummary.tone]}>{view.gateSummary.label}</Chip>}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-label">
            {view.gates.map((gate) => (
              <div key={gate.id} className="p-2.5 bg-cx-sub border border-cx-line flex items-center justify-between">
                <div>
                  <span className="font-bold text-cx-accent mr-2">{gate.id}:</span>
                  <span className="font-sans text-cx-ink font-medium">{gate.name}</span>
                </div>
                <Chip tone={gate.status === 'PASS' ? 'ok' : 'bad'}>{gate.status}</Chip>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Surface 3: Dead Letter Queue (DLQ) Quarantine & Live Redrive Inspector (Anchor: panel-dlq) */}
      <div
        role="tabpanel"
        id="panel-dlq"
        aria-label="DLQ Quarantine Inspector"
        className="block"
      >
        <section aria-label="Dead Letter Queue Inspector" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base text-amber-600">report_problem</span>
              <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
                Quarantined Dead Letter Queue (DLQ) &amp; Live Redrive Controls
              </h3>
            </div>
            <span className="px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 text-label font-bold font-mono">
              QUARANTINE DEPTH: 2 RECORDS [ILLUSTRATIVE]
            </span>
          </div>

          <div className="space-y-2">
            {[
              {
                id: 'dlq_rec_90112',
                stream: 'kafka.raw.trade_events.v2',
                error: 'Missing required field execution_price_usd',
                status: 'QUARANTINED',
                payload: '{"account_id": "ACC-99210", "symbol": "XAUUSD", "volume_lots": 1.5}',
              },
              {
                id: 'dlq_rec_90113',
                stream: 'kafka.raw.kyc_profiles.v1',
                error: 'IdP signature mismatch against public JWKS',
                status: 'QUARANTINED',
                payload: '{"client_id": "CR-SUSPECT-84920", "idp_provider": "SumSub"}',
              },
            ].map((item) => (
              <div key={item.id} className="p-3 bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{item.id}</span>
                    <span className="px-1.5 py-0.2 bg-slate-200 text-slate-700 text-label font-mono">
                      Stream: {item.stream}
                    </span>
                    <span className="px-1.5 py-0.2 bg-amber-100 text-amber-800 text-label font-mono font-bold">
                      {item.status}
                    </span>
                  </div>
                  <p className="text-label text-red-600 font-sans">Reason: {item.error}</p>
                  <code className="text-label text-slate-500 block truncate max-w-lg bg-white p-1 border border-slate-200">
                    {item.payload}
                  </code>
                  {redrive[item.id] && (
                    <p role="status" className={`text-label font-mono font-semibold ${redrive[item.id].ok ? 'text-cx-ok' : 'text-cx-bad'}`}>
                      {redrive[item.id].message}
                    </p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => redriveRecord(item.id)}
                  className="px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white font-mono text-xs font-bold transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer"
                >
                  <span className="material-symbols-sharp text-sm">replay</span>
                  Redrive Pipeline
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Surface 4: Disaster Recovery Proof Card & Chaos Fallback (Anchor: panel-dr) */}
      <div
        role="tabpanel"
        id="panel-dr"
        aria-label="Platform Disaster Recovery Proofs"
        className="block"
      >
        <div className="space-y-4">
          <DrProofCard />

          <section aria-label="System Resilience Testing" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3 font-sans">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2">
                <span className="material-symbols-sharp text-base text-amber-600">electrical_services</span>
                <h3 className="text-title font-sans font-semibold tracking-normal text-cx-ink">
                  Resilience Gate (Principle VIII) • Deterministic Fallback &amp; Partition Verification
                </h3>
              </div>
              <span className={`px-2 py-0.5 text-label font-bold font-mono border ${
                state.isSimulatedOutage
                  ? 'bg-amber-100 text-amber-900 border-amber-300'
                  : 'bg-cx-ok-bg text-cx-ok border-cx-ok-line'
              }`}>
                {state.isSimulatedOutage ? 'PARTITION ACTIVE (OFFLINE REPLAY)' : 'LIVE STREAM NOMINAL'}
              </span>
            </div>
            <p className="text-xs text-slate-600 font-sans leading-relaxed">
              Injects a simulated upstream presentation partition to test deterministic offline fallback and verified cryptographic cache replay under network severance.
            </p>
            <button
              type="button"
              onClick={() => toggleSimulatedOutage()}
              className={`px-3 py-1.5 text-xs font-mono font-medium border transition-colors flex items-center gap-1.5 cursor-pointer ${
                state.isSimulatedOutage
                  ? 'bg-amber-500 border-amber-600 text-slate-950 font-bold'
                  : 'bg-cx-sub hover:bg-cx-sub-2 border-cx-line text-cx-ink'
              }`}
            >
              <span className="material-symbols-sharp text-xs">
                {state.isSimulatedOutage ? 'bolt' : 'electrical_services'}
              </span>
              <span>{state.isSimulatedOutage ? 'Restore Live Pipeline Stream' : 'Simulate Outage & Partition Fallback'}</span>
            </button>
          </section>
        </div>
      </div>
    </div>
  );
}
