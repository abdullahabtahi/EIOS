'use client';

/**
 * Data Platform Operations Board (User Story 5 / Features 012, 015)
 * Displays Governed Lakehouse Data Product SLA freshness monitors,
 * Platform SRE SLO 28-day error budget burndowns,
 * Continuous Governance Red-Line test gates (RL-1..RL-7),
 * and Dead Letter Queue (DLQ) quarantine inspector with live redrive.
 * Strict Institutional Light Mode.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { DrProofCard } from '../common/dr-proof-card';
import { buildOperationsView, type OpsCard, type OpsStatus, type OpsTone } from '../state/operations-view-model';
import { Chip, type ChipTone } from '../ui/chip';
import { PanelHeader } from '../ui/panel-header';
import { authFetch } from '@/lib/auth/token';

interface DlqRecord {
  dlq_id: string;
  source_stream: string;
  error_message: string;
  status: string;
  payload: unknown;
}

/** The quarantined records the backend sent with the board; none when it sent none. */
function dlqRecords(canvas: unknown): DlqRecord[] {
  const data = (canvas as { data?: { dlq?: unknown } } | null)?.data;
  return Array.isArray(data?.dlq) ? (data.dlq as DlqRecord[]) : [];
}

const STATUS_TONE: Record<OpsStatus, ChipTone> = { HEALTHY: 'ok', DEGRADED: 'warn', BREACHED: 'bad', NO_DATA: 'neutral' };
const STATUS_BAR: Record<OpsStatus, string> = {
  HEALTHY: 'bg-green-600',
  DEGRADED: 'bg-amber-500',
  BREACHED: 'bg-red-600',
  NO_DATA: 'bg-slate-300',
};
const SUMMARY_TONE: Record<OpsTone, ChipTone> = { ok: 'ok', warn: 'warn', bad: 'bad' };

function renderFreshnessValue(val: string) {
  const match = val.match(/^not judged \(newest event (.*?) old\)$/i);
  if (match) {
    return (
      <span title={val} className="truncate">
        <span className="font-semibold text-slate-800">{match[1]}</span>
        <span className="text-slate-400 font-normal"> · uncalibrated</span>
      </span>
    );
  }
  return <span title={val}>{val}</span>;
}

export function OperationsBoardView() {
  const { state, toggleSimulatedOutage } = useCockpit();
  const view = React.useMemo(() => buildOperationsView(state.canvasPayload), [state.canvasPayload]);
  const [redrive, setRedrive] = React.useState<Record<string, { ok: boolean; message: string }>>({});
  const [done, setDone] = React.useState<Set<string>>(new Set());
  const records = React.useMemo(
    () => dlqRecords(state.canvasPayload).map((r) => (done.has(r.dlq_id) ? { ...r, status: 'REDRIVEN_COMMITTED' } : r)),
    [state.canvasPayload, done],
  );
  const held = records.filter((r) => r.status === 'QUARANTINED');

  const redriveRecord = async (id: string) => {
    try {
      const res = await authFetch('/api/v1/ops/dlq/redrive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dlq_id: id }),
      });
      const detail = res.ok ? '' : String((await res.json().catch(() => ({}))).detail ?? '');
      setRedrive((prev) => ({
        ...prev,
        [id]: res.ok
          ? { ok: true, message: 'Redriven through the pipeline and accepted' }
          : { ok: false, message: detail ? `Still quarantined: ${detail}` : `Redrive failed: DLQ service responded ${res.status}` },
      }));
      if (res.ok) setDone((prev) => new Set(prev).add(id));
    } catch {
      setRedrive((prev) => ({ ...prev, [id]: { ok: false, message: 'Redrive failed: DLQ service unreachable' } }));
    }
  };

  const replayAll = async () => {
    for (const item of held) {
      await redriveRecord(item.dlq_id);
    }
  };

  const renderProductCard = (card: OpsCard) => {
    const detailMap = new Map(card.details.map((d) => [d.label, d.value]));
    const slaVal = detailMap.get('SLA') ?? '—';
    const lastIngestVal = detailMap.get('Last ingest') ?? '—';
    const freshnessVal = detailMap.get('Freshness') ?? null;
    const breachesVal = detailMap.get('Contract breaches') ?? '0.00%';
    const quarantinedVal = detailMap.get('Quarantined') ?? '0';

    return (
      <div
        key={card.id}
        className="p-3.5 border border-slate-200 bg-white shadow-xs flex flex-col justify-between space-y-2.5 transition-colors hover:border-slate-300"
      >
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-slate-400 text-[11px] uppercase font-mono tracking-wider">
              <span className="material-symbols-sharp text-xs text-blue-600">database</span>
              <span>Data Product</span>
            </div>
            <Chip tone={STATUS_TONE[card.status]}>{card.status}</Chip>
          </div>
          <h4
            className="font-mono font-bold text-xs text-slate-900 break-all"
            title={card.name}
          >
            {card.name}
          </h4>
        </div>

        <div className="flex items-baseline justify-between pt-1 border-t border-slate-100">
          <span className="text-slate-500 text-[11px] font-mono shrink-0">{card.primaryLabel}:</span>
          <span className="font-mono font-bold text-sm text-slate-900 tabular-nums">
            {card.primary}
          </span>
        </div>

        <div className="space-y-1.5 pt-1.5 border-t border-slate-100 text-[11px] font-mono">
          <div className="flex justify-between items-baseline gap-2 text-slate-500">
            <span className="shrink-0">SLA:</span>
            <span className="text-slate-800 font-semibold tabular-nums">{slaVal}</span>
          </div>
          <div className="flex justify-between items-baseline gap-2 text-slate-500">
            <span className="shrink-0">Last ingest:</span>
            <span className="text-slate-800 font-semibold tabular-nums">{lastIngestVal}</span>
          </div>
          <div className="flex justify-between items-baseline gap-2 text-slate-500">
            <span className="shrink-0">Freshness:</span>
            <span className="text-slate-800 font-medium tabular-nums text-right">
              {freshnessVal ? renderFreshnessValue(freshnessVal) : 'nominal (<30s)'}
            </span>
          </div>
          <div className="flex justify-between items-baseline gap-2 text-slate-500">
            <span className="shrink-0">Contract breaches:</span>
            <span className="text-slate-800 font-semibold tabular-nums">{breachesVal}</span>
          </div>
          <div className="flex justify-between items-baseline gap-2 text-slate-500">
            <span className="shrink-0">Quarantined:</span>
            <span className="text-slate-800 font-semibold tabular-nums">{quarantinedVal}</span>
          </div>
        </div>
      </div>
    );
  };

  const renderBudgetCard = (card: OpsCard) => {
    return (
      <div
        key={card.id}
        className="p-3.5 border border-slate-200 bg-white shadow-xs flex flex-col justify-between space-y-2.5 transition-colors hover:border-slate-300"
      >
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-slate-400 text-[11px] uppercase font-mono tracking-wider">
              <span className="material-symbols-sharp text-xs text-slate-400">tune</span>
              <span>SLO Runtime Probe</span>
            </div>
            <Chip tone={STATUS_TONE[card.status]}>{card.status}</Chip>
          </div>
          <h4
            className="font-sans font-semibold text-xs leading-snug text-slate-900 min-h-[32px] flex items-center"
            title={card.name}
          >
            {card.name}
          </h4>
        </div>

        <div className="flex items-baseline justify-between pt-1 border-t border-slate-100">
          <span className="text-slate-500 text-[11px] font-mono shrink-0">Budget Left:</span>
          <span className="font-mono font-bold text-sm text-slate-900 tabular-nums">
            {card.primary}
          </span>
        </div>

        <div className="space-y-1">
          <div className="w-full h-1.5 bg-slate-100 overflow-hidden rounded-xs">
            {card.budgetRemainingPct !== null ? (
              <div
                className={`h-full transition-all duration-300 ${STATUS_BAR[card.status]}`}
                style={{ width: `${Math.max(0, Math.min(100, card.budgetRemainingPct))}%` }}
              />
            ) : (
              <div className="h-full bg-slate-200" style={{ width: '0%' }} />
            )}
          </div>
        </div>

        {card.details.length > 0 ? (
          <div className="space-y-1 pt-1 border-t border-slate-100 text-[11px] font-mono">
            {card.details.map((d) => (
              <div key={d.label} className="flex justify-between gap-2 text-slate-500">
                <span className="shrink-0">{d.label}:</span>
                <span className="text-slate-800 font-semibold tabular-nums">{d.value}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="pt-1 border-t border-slate-100 text-[11px] font-mono text-slate-400">
            &nbsp;
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6 text-slate-900 font-mono text-xs pb-10">
      {/* Surface 1: SLA Freshness Monitors & Telemetry (Anchor: panel-slos) */}
      <div
        role="tabpanel"
        id="panel-slos"
        aria-label="Data Product Freshness SLOs"
        className="block min-h-[1400px]"
      >
        <section aria-label="SLA Freshness Monitors" className="bg-white border border-slate-200 p-4 shadow-sm space-y-4">
          <PanelHeader
            icon="speed"
            title="Data Product SLA Freshness & Error Budget Burndowns"
            actions={
              <>
                <Chip tone={SUMMARY_TONE[view.summary.tone]}>{view.summary.label}</Chip>
              </>
            }
          />

          {/* Skeleton state during loading: pre-allocates dual-section grid geometry to eliminate CLS */}
          {state.isLoading && view.products.length === 0 && view.errorBudgets.length === 0 && (
            <div className="space-y-6 animate-pulse">
              {/* Domain A Skeleton: Lakehouse Data Products */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <div className="h-4 w-56 bg-slate-200 rounded-xs" />
                  <div className="h-4 w-28 bg-slate-100 rounded-xs" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
                    <div key={i} className="h-32 bg-slate-50 border border-slate-200 p-3.5 flex flex-col justify-between">
                      <div className="space-y-2">
                        <div className="h-3 w-20 bg-slate-200 rounded-xs" />
                        <div className="h-4 w-40 bg-slate-300 rounded-xs" />
                      </div>
                      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100">
                        <div className="h-3 w-16 bg-slate-200 rounded-xs" />
                        <div className="h-3 w-16 bg-slate-200 rounded-xs" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Domain B Skeleton: Platform SRE SLOs */}
              <div className="space-y-2.5 pt-2">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <div className="h-4 w-64 bg-slate-200 rounded-xs" />
                  <div className="h-4 w-28 bg-slate-100 rounded-xs" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
                    <div key={i} className="h-32 bg-slate-50 border border-slate-200 p-3.5 flex flex-col justify-between">
                      <div className="space-y-2">
                        <div className="h-3 w-24 bg-slate-200 rounded-xs" />
                        <div className="h-4 w-44 bg-slate-300 rounded-xs" />
                      </div>
                      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100">
                        <div className="h-3 w-16 bg-slate-200 rounded-xs" />
                        <div className="h-3 w-16 bg-slate-200 rounded-xs" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {!state.isLoading && view.source === 'unavailable' && (
            <p role="alert" className="p-3 text-xs bg-cx-sub border border-cx-line text-cx-muted font-sans">
              No operations data was received from the backend, so nothing is shown in its place.
            </p>
          )}

          {/* Domain A: Governed Lakehouse Data Products */}
          {view.products.length > 0 && (
            <div className="space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-sharp text-base text-blue-600">table_chart</span>
                  <h4 className="text-xs font-sans font-bold uppercase tracking-wider text-slate-800">
                    Governed Lakehouse Data Products
                  </h4>
                  <span className="text-[11px] text-slate-400 font-mono">
                    ({view.products.length} Pipelines)
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[11px] font-mono">
                  {(() => {
                    const degradedCount = view.products.filter((p) => p.status === 'DEGRADED' || p.status === 'BREACHED').length;
                    const healthyCount = view.products.filter((p) => p.status === 'HEALTHY').length;
                    return (
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-700 border border-slate-200">
                        {degradedCount > 0 && (
                          <span className="text-amber-700 font-bold mr-1.5">{degradedCount} DEGRADED ·</span>
                        )}
                        <span className="text-green-700 font-semibold">{healthyCount} HEALTHY</span>
                      </span>
                    );
                  })()}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {view.products.map(renderProductCard)}
              </div>
            </div>
          )}

          {/* Domain B: Platform SRE SLOs & 28-Day Error Budget Burndowns */}
          {view.errorBudgets.length > 0 && (
            <div className="space-y-2.5 pt-2">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-sharp text-base text-blue-600">monitoring</span>
                  <h4 className="text-xs font-sans font-bold uppercase tracking-wider text-slate-800">
                    Platform SRE SLOs &amp; Error Budget Burndowns
                  </h4>
                  <span className="text-[11px] text-slate-400 font-mono">
                    ({view.errorBudgets.length} Runtime Probes)
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[11px] font-mono">
                  {(() => {
                    const breachedCount = view.errorBudgets.filter((b) => b.status === 'BREACHED').length;
                    const healthyCount = view.errorBudgets.filter((b) => b.status === 'HEALTHY').length;
                    const noDataCount = view.errorBudgets.filter((b) => b.status === 'NO_DATA').length;
                    return (
                      <span className="px-2 py-0.5 bg-slate-100 text-slate-700 border border-slate-200">
                        {breachedCount > 0 && (
                          <span className="text-red-700 font-bold mr-1.5">{breachedCount} BREACHED ·</span>
                        )}
                        <span className="text-green-700 font-semibold">{healthyCount} HEALTHY</span>
                        {noDataCount > 0 && (
                          <span className="text-slate-500 font-normal ml-1.5">· {noDataCount} UNMEASURED</span>
                        )}
                      </span>
                    );
                  })()}
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {view.errorBudgets.map(renderBudgetCard)}
              </div>
            </div>
          )}

          {/* Fallback for unpartitioned legacy fixtures */}
          {view.products.length === 0 && view.errorBudgets.length === 0 && view.cards.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {view.cards.map(renderProductCard)}
            </div>
          )}
        </section>
      </div>

      {/* Surface 2: Red-Line Test Gates (RL-1 to RL-7) (Anchor: panel-redlines) */}
      <div
        role="tabpanel"
        id="panel-redlines"
        aria-label="Red-Line Test Gates"
        className="block min-h-[220px]"
      >
        <section aria-label="Red-Line Test Gates" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3">
          <PanelHeader
            icon="verified"
            title="Continuous Governance Red-Line Gates (RL-1 to RL-7)"
            actions={<Chip tone={SUMMARY_TONE[view.gateSummary.tone]}>{view.gateSummary.label}</Chip>}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-label">
            {view.gates.map((gate) => (
              <div
                key={gate.id}
                title={gate.basis || undefined}
                className="p-3 border border-slate-200 bg-white shadow-xs flex items-center justify-between gap-3 hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="font-mono font-bold text-slate-800 bg-slate-100 px-1.5 py-0.5 border border-slate-200 text-[11px] shrink-0">
                    {gate.id}:
                  </span>
                  <span className="font-sans text-slate-900 font-semibold text-xs truncate">
                    {gate.name}
                  </span>
                </div>
                <Chip tone={gate.status === 'PASS' ? 'ok' : gate.status === 'FAIL' ? 'bad' : 'neutral'}>
                  {gate.status === 'NOT_MEASURED' ? 'NOT MEASURED' : gate.status}
                </Chip>
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
        className="block min-h-[160px]"
      >
        <section aria-label="Dead Letter Queue Inspector" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base text-amber-600">report_problem</span>
              <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
                Quarantined Dead Letter Queue (DLQ) &amp; Redrive
              </h3>
            </div>
            <div className="flex items-center gap-2">
              {held.length > 1 && (
                <button
                  type="button"
                  onClick={replayAll}
                  className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-white font-mono text-[11px] font-bold transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer"
                >
                  <span className="material-symbols-sharp text-xs">playlist_play</span>
                  Replay All ({held.length})
                </button>
              )}
              <span className="px-2 py-0.5 bg-amber-50 text-amber-800 border border-amber-200 text-label font-bold font-mono">
                QUARANTINE DEPTH: {held.length} {held.length === 1 ? 'RECORD' : 'RECORDS'}
              </span>
            </div>
          </div>

          {records.length === 0 && (
            <p className="text-xs text-cx-muted font-sans">No records are quarantined.</p>
          )}
          <div className="space-y-2">
            {records.map((item) => (
              <div key={item.dlq_id} className="p-3 bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="space-y-1.5 min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-slate-900">{item.dlq_id.slice(0, 8)}</span>
                    <span className="px-1.5 py-0.5 bg-slate-200 text-slate-700 text-label font-mono">
                      Stream: {item.source_stream}
                    </span>
                    <span className="px-1.5 py-0.5 bg-amber-100 text-amber-800 text-label font-mono font-bold">
                      {item.status}
                    </span>
                  </div>
                  <p className="text-label text-red-600 font-sans font-medium">Reason: {item.error_message}</p>
                  <details className="text-xs group">
                    <summary className="cursor-pointer select-none font-mono text-slate-500 hover:text-slate-800 flex items-center gap-1 text-[11px] py-0.5">
                      <span className="material-symbols-sharp text-xs transition-transform group-open:rotate-90">chevron_right</span>
                      <span>Payload inspector ({typeof item.payload === 'object' && item.payload ? Object.keys(item.payload).length : 1} fields)</span>
                    </summary>
                    <pre className="mt-1 p-2 bg-slate-900 text-slate-100 font-mono text-[11px] border border-slate-700 overflow-x-auto rounded-xs max-h-48">
                      {JSON.stringify(item.payload, null, 2)}
                    </pre>
                  </details>
                  {redrive[item.dlq_id] && (
                    <p role="status" className={`text-label font-mono font-semibold ${redrive[item.dlq_id].ok ? 'text-cx-ok' : 'text-cx-bad'}`}>
                      {redrive[item.dlq_id].message}
                    </p>
                  )}
                </div>

                {item.status === 'QUARANTINED' && (
                  <button
                    type="button"
                    onClick={() => redriveRecord(item.dlq_id)}
                    className="px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white font-mono text-xs font-bold transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer shrink-0"
                  >
                    <span className="material-symbols-sharp text-sm">replay</span>
                    Redrive
                  </button>
                )}
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
        className="block min-h-[200px]"
      >
        <div className="space-y-4">
          <DrProofCard proof={state.activeDrProofs[0]} />

          <section aria-label="System Resilience Testing" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3 font-sans">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
              <div className="flex items-center gap-2">
                <span className="material-symbols-sharp text-base text-amber-600">electrical_services</span>
                <h3 className="text-title font-sans font-semibold tracking-normal text-cx-ink">
                  Resilience Gate • Deterministic Fallback &amp; Partition Verification
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
